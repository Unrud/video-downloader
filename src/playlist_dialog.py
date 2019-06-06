# playlist_dialog.py
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
import tkinter as tk
from tkinter import ttk

from video_downloader import PAD
from video_downloader.base_dialog import BaseDialog

g_ = gettext.gettext


class PlaylistDialog(BaseDialog):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(g_("Video Downloader"))
        self.resizable(False, False)
        self.create_widgets()
        self.focus_set()

    def focus_set(self):
        self.yes_button.focus_set()

    def create_widgets(self):
        content = ttk.Frame(self)
        title_label = ttk.Label(
            content, style="Title.TLabel",
            text=g_("Download complete playlist?"))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        title_label.grid(column=0, row=0, columnspan=2, padx=PAD, pady=PAD)
        self.yes_button = ttk.Button(
            content, text=g_("Yes"), command=self.on_yes)
        self.yes_button.grid(column=0, row=1, sticky=tk.W+tk.E)
        self.no_button = ttk.Button(content, text=g_("No"), command=self.on_no)
        self.no_button.grid(column=1, row=1, sticky=tk.W+tk.E)
        content.pack(expand=1, fill=tk.BOTH)

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()
