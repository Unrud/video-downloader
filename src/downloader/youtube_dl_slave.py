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
import sys
import tempfile

import youtube_dl

from video_downloader.downloader import MAX_RESOLUTION
from video_downloader.downloader.youtube_dl_formats import sort_formats

OUTPUT_TEMPLATE = '%(title)s-%(id)s-%(format_id)s.%(ext)s'


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
                progress = bytes_ / bytes_total
            elif fragments >= 0 and fragments_total >= 0:
                progress = fragments / fragments_total
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

    def _load_playlist(self, dir_, ydl_opts, url=None, info_path=None):
        os.chdir(dir_)
        while True:
            try:
                if url is not None:
                    youtube_dl.YoutubeDL(ydl_opts).download([url])
                else:
                    youtube_dl.YoutubeDL(ydl_opts).download_with_info_file(
                        info_path)
            except youtube_dl.utils.DownloadError as e:
                if 'username' not in ydl_opts and (
                        'please sign in' in str(e) or
                        '--username' in str(e)):
                    ydl_opts['username'], ydl_opts['password'] = (
                        self._handler.on_login_request())
                if 'videopassword' not in ydl_opts and (
                        '--video-password' in str(e)):
                    ydl_opts['videopassword'] = (
                        self._handler.on_videopassword_request())
                    continue
                raise
            break
        return sorted(map(os.path.abspath, glob.iglob('*.info.json')))

    def debug(self, msg):
        # For ydl_opts['forcejson']
        if self._expect_info_dict_json:
            self._expect_info_dict_json = False
            self._info_dict = json.loads(msg)
            return
        print(msg, file=sys.stderr, flush=True)

    def warning(self, msg):
        print(msg, file=sys.stderr, flush=True)

    def error(self, msg):
        print(msg, file=sys.stderr, flush=True)
        self._handler.on_error(msg)

    def __init__(self):
        self._handler = Handler()
        # See ydl_opts['forcejson']
        self._expect_info_dict_json = False
        self._info_dict = None
        ydl_opts = {
            'logger': self,
            'logtostderr': True,
            'no_color': True,
            'progress_hooks': [self._on_progress],
            'writeinfojson': True,
            'writethumbnail': True,
            'skip_download': True,
            'playlistend': 2,
            'outtmpl': '%(autonumber)s.%(ext)s',
            'fixup': 'detect_or_warn',
            'postprocessors': [{'key': 'XAttrMetadata'}]}
        url = self._handler.get_url()
        target_dir = os.path.abspath(self._handler.get_target_dir())
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts['cookiefile'] = os.path.join(temp_dir, 'cookies')
            testplaylist_dir = os.path.join(temp_dir, 'testplaylist')
            noplaylist_dir = os.path.join(temp_dir, 'noplaylist')
            fullplaylist_dir = os.path.join(temp_dir, 'fullplaylist')
            for path in [testplaylist_dir, noplaylist_dir, fullplaylist_dir]:
                os.mkdir(path)
            # Test playlist
            info_testplaylist = self._load_playlist(
                testplaylist_dir, ydl_opts, url)
            ydl_opts['noplaylist'] = True
            if len(info_testplaylist) > 1:
                info_noplaylist = self._load_playlist(
                    noplaylist_dir, ydl_opts, url)
            else:
                info_noplaylist = info_testplaylist
            del ydl_opts['noplaylist']
            del ydl_opts['playlistend']
            if len(info_testplaylist) > len(info_noplaylist):
                ydl_opts['noplaylist'] = (
                    not self._handler.on_playlist_request())
                if not ydl_opts['noplaylist']:
                    info_playlist = self._load_playlist(
                        fullplaylist_dir, ydl_opts, url)
                else:
                    info_playlist = info_noplaylist
            elif len(info_testplaylist) > 1:
                info_playlist = self._load_playlist(
                    fullplaylist_dir, ydl_opts, url)
            else:
                info_playlist = info_testplaylist
            del ydl_opts['writeinfojson']
            del ydl_opts['writethumbnail']
            del ydl_opts['skip_download']
            ydl_opts['outtmpl'] = OUTPUT_TEMPLATE
            # Output info_dict as JSON with debug method of logger
            ydl_opts['forcejson'] = True
            mode = self._handler.get_mode()
            resolution = self._handler.get_resolution()
            if mode == 'audio':
                resolution = MAX_RESOLUTION
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'].insert(0, {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'})
                ydl_opts['postprocessors'].insert(1, {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': True})
            os.makedirs(target_dir, exist_ok=True)
            for i, info_path in enumerate(info_playlist):
                with open(info_path) as f:
                    info = json.load(f)
                title = info.get('title', info.get('id', 'video'))
                thumbnail_paths = list(filter(
                    lambda p: os.path.splitext(p)[1][1:] != 'json', glob.iglob(
                        glob.escape(info_path[:-len('info.json')]) + '*')))
                thumbnail_path = thumbnail_paths[0] if thumbnail_paths else ''
                self._handler.on_progress_start(i, len(info_playlist), title,
                                                thumbnail_path)
                if info.get('thumbnails'):
                    info['thumbnails'][-1]['filename'] = thumbnail_path
                sort_formats(info['formats'], resolution=resolution)
                with open(info_path, 'w') as f:
                    json.dump(info, f)
                # See ydl_opts['forcejson']
                self._expect_info_dict_json = True
                self._load_playlist(target_dir, ydl_opts, info_path=info_path)
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
