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


class YoutubeDLSlave:
    def on_progress(self, d):
        if d["status"] not in ["downloading", "finished"]:
            return
        filename = d["filename"]
        bytes_ = d.get("downloaded_bytes")
        if bytes_ is None:
            bytes_ = -1
        bytes_total = d.get("total_bytes")
        if bytes_total is None:
            bytes_total = d.get("total_bytes_estimate")
        if bytes_total is None:
            bytes_total = -1
        if d["status"] == "downloading":
            fragments = d.get("fragment_index")
            if fragments is None:
                fragments = -1
            fragments_total = d.get("fragment_count")
            if fragments_total is None:
                fragments_total = -1
            if bytes_ >= 0 and bytes_total >= 0:
                progress = 100 * bytes_ // bytes_total
            elif fragments >= 0 and fragments_total >= 0:
                progress = 100 * fragments // fragments_total
            else:
                progress = -1
            eta = d.get("eta")
            if eta is None:
                eta = -1
            speed = d.get("speed")
            if speed is None:
                speed = -1
            speed = round(speed)
        elif d["status"] == "finished":
            progress = -1
            eta = -1
            speed = -1
        self.handler.on_progress(
            filename, progress, bytes_, bytes_total, eta, speed)

    def load_playlist(self, dir_, ydl_opts, url=None, info_path=None):
        os.chdir(dir_)
        while True:
            try:
                if url is not None:
                    youtube_dl.YoutubeDL(ydl_opts).download([url])
                else:
                    youtube_dl.YoutubeDL(ydl_opts).download_with_info_file(
                        info_path)
            except youtube_dl.utils.DownloadError as e:
                if "--username" in str(e) and "username" not in ydl_opts:
                    ydl_opts["username"], ydl_opts["password"] = (
                        self.handler.on_login_request())
                if ("--video-password" in str(e) and
                        "videopassword" not in ydl_opts):
                    ydl_opts["videopassword"] = (
                        self.handler.on_videopassword_request())
                    continue
                raise
            break
        return sorted(map(os.path.abspath, glob.iglob("*.json")))

    def debug(self, msg):
        print(msg, file=sys.stderr)

    def warning(self, msg):
        print(msg, file=sys.stderr)

    def error(self, msg):
        print(msg, file=sys.stderr)
        self.handler.on_error(msg)

    def __init__(self):
        self.handler = Handler()
        ydl_opts = {
            "logger": self,
            "logtostderr": True,
            "no_color": True,
            "progress_hooks": [self.on_progress],
            "writeinfojson": True,
            "skip_download": True,
            "playlistend": 2,
            "outtmpl": "%(autonumber)s.%(ext)s",
            "fixup": "detect_or_warn"
        }
        url = self.handler.get_url()
        target_dir = os.path.abspath(self.handler.get_target_dir())
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts["cookiefile"] = os.path.join(temp_dir, "cookies")
            testplaylist_dir = os.path.join(temp_dir, "testplaylist")
            noplaylist_dir = os.path.join(temp_dir, "noplaylist")
            yesplaylist_dir = os.path.join(temp_dir, "yesplaylist")
            for path in [testplaylist_dir, noplaylist_dir, yesplaylist_dir]:
                os.mkdir(path)
            # Test playlist
            info_testplaylist = self.load_playlist(
                testplaylist_dir, ydl_opts, url)
            ydl_opts["noplaylist"] = True
            if len(info_testplaylist) > 1:
                info_noplaylist = self.load_playlist(
                    noplaylist_dir, ydl_opts, url)
            else:
                info_noplaylist = info_testplaylist
            del ydl_opts["noplaylist"]
            del ydl_opts["playlistend"]
            if len(info_testplaylist) > len(info_noplaylist):
                ydl_opts["noplaylist"] = not self.handler.on_playlist_request()
                if not ydl_opts["noplaylist"]:
                    info_yesplaylist = self.load_playlist(
                        yesplaylist_dir, ydl_opts, url)
                else:
                    info_yesplaylist = info_noplaylist
                info_playlist = info_yesplaylist
            else:
                info_playlist = info_yesplaylist = info_testplaylist
            del ydl_opts["writeinfojson"]
            del ydl_opts["skip_download"]
            del ydl_opts["outtmpl"]
            mode = self.handler.get_mode()
            resolution = self.handler.get_resolution()
            if mode == "audio":
                resolution = MAX_RESOLUTION
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }]
                })
            for i, info_path in enumerate(info_playlist):
                self.handler.on_playlist_progress(i, len(info_playlist))
                with open(info_path) as f:
                    info = json.load(f)
                sort_formats(info["formats"], resolution=resolution)
                with open(info_path, "w") as f:
                    json.dump(info, f)
                self.load_playlist(target_dir, ydl_opts, info_path=info_path)


class Handler:
    def _rpc(self, name, *args):
        print(json.dumps({"method": name, "args": args}), flush=True)
        answer = json.loads(sys.stdin.readline())
        return answer["result"]

    def __getattr__(self, name):
        return functools.partial(self._rpc, name)
