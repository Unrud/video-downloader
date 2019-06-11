# model.py
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

import gettext
import os
import subprocess
import threading
import tkinter as tk
import typing

from video_downloader import downloader
from video_downloader.downloader import MAX_RESOLUTION
from video_downloader.utils import sanitize_str_for_tk

g_ = gettext.gettext


class Model(downloader.Handler):
    def __init__(self, master, handler):
        self.master = master
        self.handler = handler
        self.mainloop_thread = threading.current_thread()
        # "main", "download", "error", "success":
        self.page = tk.StringVar(self.master)
        self.page.set("main")
        self.url = tk.StringVar(self.master)
        self.mode = tk.StringVar(self.master)  # "audio", "video"
        self.mode.set("audio")
        self.resolutions = [(g_("Max"), MAX_RESOLUTION),
                            (g_("4320p (8K)"), 4320),
                            (g_("2160p (4K)"), 2160),
                            (g_("1440p (HD)"), 1440),
                            (g_("1080p (HD)"), 1080),
                            (g_("720p (HD)"), 720),
                            (g_("480p"), 480),
                            (g_("360p"), 360),
                            (g_("240p"), 240),
                            (g_("144p"), 144)]
        self.resolutionIndex = tk.IntVar(self.master)
        self.resolutionIndex.set(4)
        self.error = tk.StringVar(self.master)
        self.download_playlist_index = tk.IntVar(self.master)
        self.download_playlist_count = tk.IntVar(self.master)
        self.download_filename = tk.StringVar(self.master)
        # 0-100 (inclusive), -1 if unknown:
        self.download_progress = tk.IntVar(self.master)
        self.download_bytes = tk.IntVar(self.master)  # -1 if unknown
        self.download_bytes_total = tk.IntVar(self.master)  # -1 if unknown
        self.download_speed = tk.IntVar(self.master)  # -1 if unknown
        self.download_eta = tk.IntVar(self.master)  # -1 if unknown
        self.download_target_dir = tk.StringVar(self.master)
        try:
            download_dir = subprocess.check_output(
                ["xdg-user-dir", "DOWNLOAD"], universal_newlines=True,
                stdin=subprocess.DEVNULL).splitlines()[0]
        except FileNotFoundError:
            download_dir = os.path.expanduser(os.path.join("~", "Downloads"))
        self.download_target_dir.set(os.path.abspath(
            os.path.join(download_dir, "VideoDownloader")))
        self.cancelled = False
        self.downloader = None

    def call_in_mainloop(fn):
        def fn_wrapper(self, *args, **kwargs):
            if threading.current_thread() is self.mainloop_thread:
                return fn(self, *args, **kwargs)
            result_condition = threading.Condition()
            result = None

            def result_wrapper():
                nonlocal result
                temp = fn(self, *args, **kwargs)
                with result_condition:
                    result = temp
                    result_condition.notify_all()

            with result_condition:
                self.master.after_idle(result_wrapper)
                result_condition.wait()
                return result
        return fn_wrapper

    def start(self):
        assert self.page.get() == "main"
        assert self.downloader is None
        self.error.set("")
        self.cancelled = False
        self.download_playlist_index.set(0)
        self.download_playlist_count.set(0)
        self.download_filename.set("")
        self.download_progress.set(-1)
        self.download_bytes.set(-1)
        self.download_bytes_total.set(-1)
        self.download_speed.set(-1)
        self.download_eta.set(-1)
        self.page.set("download")
        self.downloader = downloader.Downloader(self)
        self.downloader.start()

    def cancel(self):
        assert self.page.get() == "download"
        assert self.downloader is not None
        self.cancelled = True
        self.downloader.cancel()

    def back_to_main(self):
        assert self.page.get() in ["error", "success"]
        assert self.downloader is None
        self.page.set("main")

    @call_in_mainloop
    def get_target_dir(self):
        assert self.page.get() == "download"
        return self.download_target_dir.get()

    @call_in_mainloop
    def get_url(self):
        assert self.page.get() == "download"
        return self.url.get()

    @call_in_mainloop
    def get_mode(self):
        assert self.page.get() == "download"
        return self.mode.get()

    @call_in_mainloop
    def get_resolution(self):
        assert self.page.get() == "download"
        _, resolution = self.resolutions[self.resolutionIndex.get()]
        return resolution

    @call_in_mainloop
    def on_playlist_request(self):
        assert self.page.get() == "download"
        return self.handler.on_playlist_request()

    @call_in_mainloop
    def on_login_request(self):
        assert self.page.get() == "download"
        return self.handler.on_login_request()

    @call_in_mainloop
    def on_videopassword_request(self):
        assert self.page.get() == "download"
        return self.handler.on_videopassword_request()

    @call_in_mainloop
    def on_error(self, msg):
        assert self.page.get() == "download"
        self.error.set(sanitize_str_for_tk(msg))

    @call_in_mainloop
    def on_progress(self, filename, progress, bytes_, bytes_total, eta, speed):
        assert self.page.get() == "download"
        self.download_filename.set(sanitize_str_for_tk(filename))
        self.download_progress.set(progress)
        self.download_bytes.set(bytes_)
        self.download_bytes_total.set(bytes_total)
        self.download_eta.set(eta)
        self.download_speed.set(speed)

    @call_in_mainloop
    def on_playlist_progress(self, playlist_index, playlist_count):
        assert self.page.get() == "download"
        self.download_playlist_index.set(playlist_index)
        self.download_playlist_count.set(playlist_count)

    @call_in_mainloop
    def on_finished(self, success):
        assert self.page.get() == "download"
        assert self.downloader is not None
        self.downloader = None
        if not success and self.cancelled:
            self.page.set("main")
            return
        self.page.set("success" if success else "error")


class Handler:
    def on_playlist_request(self) -> bool:
        raise NotImplementedError

    #                                          username password
    def on_login_request(self) -> typing.Tuple[str,     str]:
        raise NotImplementedError

    #                                     password
    def on_videopassword_request(self) -> str:
        raise NotImplementedError
