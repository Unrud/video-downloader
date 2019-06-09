# download_frame.py
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

import datetime
import gettext
import tkinter as tk
from tkinter import ttk

from video_downloader import PAD, WRAPLENGTH

g_ = gettext.gettext


class DownloadFrame(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.create_widgets()

    def focus_set(self):
        self.cancel_button.focus_set()

    def on_download_progress_changed(self, *_):
        download_progress = self.master.model.download_progress.get()
        if download_progress < 0:
            self.download_progressbar.config(mode="indeterminate")
        else:
            self.download_progress_internal.set(download_progress)
            self.download_progressbar.config(mode="determinate")
        if (self.master.model.page.get() == "download" and
                download_progress < 0):
            self.download_progressbar.start()
        else:
            self.download_progressbar.stop()

    def on_download_bytes_changed(self, *_):
        def filesize_fmt(num, suffix="B"):
            for unit in ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]:
                if abs(num) < 1000:
                    break
                num /= 1000
            return "%s %s%s" % (round(num, 1), unit, suffix)

        bytes_ = self.master.model.download_bytes.get()
        bytes_total = self.master.model.download_bytes_total.get()
        speed = self.master.model.download_speed.get()
        eta = self.master.model.download_eta.get()
        if bytes_ >= 0:
            bytes_text = filesize_fmt(bytes_)
        else:
            bytes_text = g_("unknown")
        if bytes_total >= 0:
            bytes_total_text = filesize_fmt(bytes_total)
        else:
            bytes_total_text = g_("unknown")
        if bytes_ >= 0 or bytes_total >= 0:
            text = "{} of {}".format(bytes_text, bytes_total_text)
        else:
            text = ""
        if speed >= 0:
            if text:
                text += " "
            text += "({})" .format(filesize_fmt(speed, "B/s"))
        if eta >= 0:
            if text:
                text = " - " + text
            text = str(datetime.timedelta(seconds=eta)) + text
        self.download_bytes_label.config(text=text)

    def on_download_title_changed(self, *_):
        filename = self.master.model.download_title.get()
        playlist_count = self.master.model.download_playlist_count.get()
        playlist_index = self.master.model.download_playlist_index.get()
        title = g_("Downloading")
        if playlist_count > 1:
            title = "{} ({} of {})".format(title, playlist_index + 1,
                                           playlist_count)
        if filename:
            title = "{}: {}".format(title, filename)
        if len(title) > WRAPLENGTH:
            title = title[:WRAPLENGTH - 1] + "…"
        self.download_title_label.config(text=title)

    def create_widgets(self):
        self.download_progress_internal = tk.IntVar(self)

        header = ttk.Frame(self)
        title_label = None
        if self.master.platform.custom_titlebar:
            title_label = ttk.Label(header, style="Header.Title.TLabel",
                                    text=g_("Video Downloader"))
            self.master.bind_window_drag_handler(title_label)
        self.cancel_button = ttk.Button(
            header, style="Header.TButton", text=g_("Abbrechen"),
            command=self.master.model.cancel)
        self.master.make_header(header, self.cancel_button, title_label)
        header.pack(fill=tk.X, side=tk.TOP)
        self.download_title_label = ttk.Label(self, style="Title.TLabel")
        self.download_title_label.pack(anchor=tk.W, side=tk.TOP, padx=PAD,
                                       pady=PAD)
        self.download_progressbar = ttk.Progressbar(
            self, variable=self.download_progress_internal)
        self.download_progressbar.pack(fill=tk.X, side=tk.TOP, padx=PAD,
                                       pady=PAD)
        self.download_bytes_label = ttk.Label(self)
        self.download_bytes_label.pack(anchor=tk.W, side=tk.TOP, padx=PAD,
                                       pady=PAD)
        self.master.model.download_title.trace(
            "w", self.on_download_title_changed)
        self.master.model.download_playlist_count.trace(
            "w", self.on_download_title_changed)
        self.master.model.download_playlist_index.trace(
            "w", self.on_download_title_changed)
        self.on_download_title_changed()
        self.master.model.download_progress.trace(
            "w", self.on_download_progress_changed)
        self.master.model.page.trace("w", self.on_download_progress_changed)
        self.on_download_progress_changed()
        self.master.model.download_bytes.trace(
            "w", self.on_download_bytes_changed)
        self.master.model.download_bytes_total.trace(
            "w", self.on_download_bytes_changed)
        self.master.model.download_speed.trace(
            "w", self.on_download_bytes_changed)
        self.master.model.download_eta.trace(
            "w", self.on_download_bytes_changed)
        self.on_download_bytes_changed()
