# downloader/youtube_dl_slave.py
#
# Copyright 2019 Unrud <unrud@outlook.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import functools
import glob
import json
import os
import subprocess
import sys
import tempfile
import traceback

import youtube_dl

from video_downloader.downloader import MAX_RESOLUTION
from video_downloader.downloader.youtube_dl_formats import sort_formats

OUTPUT_TEMPLATE = '%(output_title)s-%(id)s-%(format_id)s.%(ext)s'
MAX_OUTPUT_TITLE_LENGTH = 150  # File names are typically limited to 255 bytes
MAX_THUMBNAIL_RESOLUTION = 1024
CONVERT_EXE = 'convert'


class RetryException(BaseException):
    pass


class YoutubeDLSlave:
    def _on_progress(self, d):
        if d['status'] not in ['downloading', 'finished']:
            return
        filename = d['filename']
        bytes_ = d.get('downloaded_bytes')
        if bytes_ is None:
            bytes_ = -1
        bytes_total = d.get('total_bytes')
        if bytes_total is None:
            bytes_total = d.get('total_bytes_estimate')
        if bytes_total is None:
            bytes_total = -1
        if d['status'] == 'downloading':
            fragments = d.get('fragment_index')
            if fragments is None:
                fragments = -1
            fragments_total = d.get('fragment_count')
            if fragments_total is None:
                fragments_total = -1
            if bytes_ >= 0 and bytes_total >= 0:
                progress = bytes_ / bytes_total if bytes_total > 0 else -1
            elif fragments >= 0 and fragments_total >= 0:
                progress = (fragments / fragments_total
                            if fragments_total > 0 else -1)
            else:
                progress = -1
            eta = d.get('eta')
            if eta is None:
                eta = -1
            speed = d.get('speed')
            if speed is None:
                speed = -1
            speed = round(speed)
        elif d['status'] == 'finished':
            progress = -1
            eta = -1
            speed = -1
        self._handler.on_load_progress(
            filename, progress, bytes_, bytes_total, eta, speed)

    def _load_playlist(self, dir_, url=None, info_path=None):
        os.chdir(dir_)
        while True:
            try:
                saved_skipped_count = self._skipped_count
                if url is not None:
                    youtube_dl.YoutubeDL(self.ydl_opts).download([url])
                else:
                    youtube_dl.YoutubeDL(
                        self.ydl_opts).download_with_info_file(info_path)
            except RetryException:
                continue
            break
        return (sorted(map(os.path.abspath, glob.iglob('*.info.json'))),
                self._skipped_count - saved_skipped_count)

    def debug(self, msg):
        # See ydl_opts['forcejson']
        if self._expect_info_dict_json:
            self._expect_info_dict_json = False
            self._info_dict = json.loads(msg)
            return
        print(msg, file=sys.stderr, flush=True)

    def warning(self, msg):
        print(msg, file=sys.stderr, flush=True)

    def error(self, msg):
        print(msg, file=sys.stderr, flush=True)
        # Handle authentication requests
        if self._allow_authentication_request and (
                'please sign in' in msg or '--username' in msg):
            if self._skip_authentication:
                self._skipped_count += 1
                return
            user, password = self._handler.on_login_request()
            if not user and not password:
                self._skip_authentication = True
                self._skipped_count += 1
                return
            self.ydl_opts['username'] = user
            self.ydl_opts['password'] = password
            self._allow_authentication_request = False
            raise RetryException(msg)
        if self._allow_authentication_request and '--video-password' in msg:
            if self._skip_authentication:
                self._skipped_count += 1
                return
            videopassword = self._handler.on_videopassword_request()
            if not videopassword:
                self._skip_authentication = True
                self._skipped_count += 1
                return
            self.ydl_opts['videopassword'] = videopassword
            self._allow_authentication_request = False
            raise RetryException(msg)
        self._handler.on_error(msg)
        raise youtube_dl.utils.DownloadError(msg)

    def __init__(self):
        self._handler = Handler()
        # See ydl_opts['forcejson']
        self._expect_info_dict_json = False
        self._info_dict = None
        self._allow_authentication_request = True
        self._skip_authentication = False
        self._skipped_count = 0
        self.ydl_opts = {
            'logger': self,
            'logtostderr': True,
            'no_color': True,
            'progress_hooks': [self._on_progress],
            'fixup': 'detect_or_warn',
            'ignoreerrors': True,  # handled via logger error callback
            'retries': 10,
            'fragment_retries': 10,
            'postprocessors': [{'key': 'XAttrMetadata'}]}
        url = self._handler.get_url()
        target_dir = os.path.abspath(self._handler.get_target_dir())
        with tempfile.TemporaryDirectory() as temp_dir:
            self.ydl_opts['cookiefile'] = os.path.join(temp_dir, 'cookies')
            # Collect info without downloading videos
            testplaylist_dir = os.path.join(temp_dir, 'testplaylist')
            noplaylist_dir = os.path.join(temp_dir, 'noplaylist')
            fullplaylist_dir = os.path.join(temp_dir, 'fullplaylist')
            for path in [testplaylist_dir, noplaylist_dir, fullplaylist_dir]:
                os.mkdir(path)
            self.ydl_opts['writeinfojson'] = True
            self.ydl_opts['writethumbnail'] = True
            self.ydl_opts['skip_download'] = True
            self.ydl_opts['playlistend'] = 2
            self.ydl_opts['outtmpl'] = '%(autonumber)s.%(ext)s'
            # Test playlist
            info_testplaylist, skipped_testplaylist = self._load_playlist(
                testplaylist_dir, url)
            self.ydl_opts['noplaylist'] = True
            if len(info_testplaylist) + skipped_testplaylist > 1:
                info_noplaylist, skipped_noplaylist = self._load_playlist(
                    noplaylist_dir, url)
            else:
                info_noplaylist = info_testplaylist
                skipped_noplaylist = skipped_testplaylist
            del self.ydl_opts['noplaylist']
            del self.ydl_opts['playlistend']
            if (len(info_testplaylist) + skipped_testplaylist >
                    len(info_noplaylist) + skipped_noplaylist):
                self.ydl_opts['noplaylist'] = (
                    not self._handler.on_playlist_request())
                if not self.ydl_opts['noplaylist']:
                    info_playlist, _ = self._load_playlist(
                        fullplaylist_dir, url)
                else:
                    info_playlist = info_noplaylist
            elif len(info_testplaylist) + skipped_testplaylist > 1:
                info_playlist, _ = self._load_playlist(fullplaylist_dir, url)
            else:
                info_playlist = info_testplaylist
            # Download videos
            self._allow_authentication_request = False
            del self.ydl_opts['writeinfojson']
            del self.ydl_opts['writethumbnail']
            del self.ydl_opts['skip_download']
            self.ydl_opts['outtmpl'] = OUTPUT_TEMPLATE
            # Output info_dict as JSON handled via logger debug callback
            self.ydl_opts['forcejson'] = True
            mode = self._handler.get_mode()
            if mode == 'audio':
                resolution = MAX_RESOLUTION
                prefer_mpeg = False
                self.ydl_opts['format'] = 'bestaudio/best'
                self.ydl_opts['postprocessors'].insert(0, {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'})
                self.ydl_opts['postprocessors'].insert(1, {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': True})
            else:
                resolution = self._handler.get_resolution()
                prefer_mpeg = self._handler.get_prefer_mpeg()
            os.makedirs(target_dir, exist_ok=True)
            for i, info_path in enumerate(info_playlist):
                with open(info_path) as f:
                    info = json.load(f)
                title = info.get('title', info.get('id', 'video'))
                thumbnail_paths = list(filter(
                    lambda p: os.path.splitext(p)[1][1:] != 'json', glob.iglob(
                        glob.escape(info_path[:-len('info.json')]) + '*')))
                thumbnail_path = thumbnail_paths[0] if thumbnail_paths else ''
                if thumbnail_path:
                    # Convert thumbnail to JPEG and limit resolution
                    new_thumbnail_path = thumbnail_path + '-converted.jpg'
                    try:
                        subprocess.run(
                            [CONVERT_EXE, '-alpha', 'remove',
                             os.path.abspath(thumbnail_path), '-resize',
                             '{0}>x{0}>'.format(MAX_THUMBNAIL_RESOLUTION),
                             os.path.abspath(new_thumbnail_path)],
                            check=True, stdin=subprocess.DEVNULL,
                            stdout=sys.stderr)
                    except FileNotFoundError:
                        self._handler.on_error(
                            'ERROR: %r not found. Please install ImageMagick.'
                            % CONVERT_EXE)
                        raise
                    except subprocess.CalledProcessError:
                        traceback.print_exc(file=sys.stderr)
                        new_thumbnail_path = ''
                    # No longer needed
                    os.remove(thumbnail_path)
                    thumbnail_path = new_thumbnail_path
                self._handler.on_progress_start(i, len(info_playlist), title,
                                                thumbnail_path)
                for thumbnail in info.get('thumbnails') or []:
                    thumbnail['filename'] = thumbnail_path
                sort_formats(info.get('formats') or [], resolution,
                             prefer_mpeg)
                # Limit length of title in output file name
                for i in range(len(title), -1, -1):
                    info['output_title'] = title[:i]
                    if i < len(title):
                        info['output_title'] += '…'
                    # Check length with file system encoding
                    if (len(info['output_title'].encode(
                                sys.getfilesystemencoding(), 'ignore')) <
                            MAX_OUTPUT_TITLE_LENGTH):
                        break
                with open(info_path, 'w') as f:
                    json.dump(info, f)
                # See ydl_opts['forcejson']
                self._expect_info_dict_json = True
                self._load_playlist(target_dir, info_path=info_path)
                if self._expect_info_dict_json:
                    raise RuntimeError('info_dict not received')
                filename = self._info_dict['_filename']
                if mode == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'
                self._handler.on_progress_end(filename)
                self._info_dict = None


class Handler:
    def _rpc(self, name, *args):
        print(json.dumps({'method': name, 'args': args}), flush=True)
        answer = json.loads(sys.stdin.readline())
        return answer['result']

    def __getattr__(self, name):
        return functools.partial(self._rpc, name)
