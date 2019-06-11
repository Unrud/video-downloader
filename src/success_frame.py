# success_frame.py
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
import tkinter as tk
from tkinter import ttk

from video_downloader import PAD
from video_downloader.resize_label import ResizeLabel

g_ = gettext.gettext


class SuccessFrame(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.create_widgets()

    def focus_set(self):
        self.back_button.focus_set()

    def on_download_target_dir_changed(self, *_):
        download_target_dir = self.master.model.download_target_dir.get()
        user_dir = os.path.expanduser("~")
        if os.path.commonpath([user_dir, download_target_dir]) == user_dir:
            download_target_dir = "~" + download_target_dir[len(user_dir):]
        self.message_label.text = g_("Saved in {}").format(download_target_dir)

    def create_widgets(self):
        header = ttk.Frame(self)
        title_label = None
        if self.master.platform.custom_titlebar:
            title_label = ttk.Label(header, style="Header.Title.TLabel",
                                    text=g_("Video Downloader"))
            self.master.bind_window_drag_handler(title_label)
        self.back_button = ttk.Button(
            header, style="Header.TButton", text=g_("Back"),
            command=self.master.model.back_to_main)
        self.master.make_header(header, self.back_button, title_label)
        self.columnconfigure(1, weight=1)
        header.grid(column=0, row=0, columnspan=2, sticky=tk.W+tk.E)
        self.icon_label = ttk.Label(self, style="Icon.TLabel", text="✓")
        self.icon_label.grid(column=0, row=1, rowspan=2, sticky=tk.N, padx=PAD,
                             pady=PAD)
        self.message_title_label = ttk.Label(
            self, style="Title.TLabel", text=g_("Download finished"))
        self.message_title_label.grid(column=1, row=1, sticky=tk.W, padx=PAD,
                                      pady=PAD)
        self.message_label = ResizeLabel(self)
        self.message_label.grid(column=1, row=2, sticky=tk.N+tk.W+tk.E,
                                padx=PAD, pady=PAD)
        self.master.model.download_target_dir.trace(
            "w", self.on_download_target_dir_changed)
        self.on_download_target_dir_changed()
