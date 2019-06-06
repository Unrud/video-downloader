# videopassword_dialog.py
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


class VideopasswordDialog(BaseDialog):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(g_("Video Downloader"))
        self.resizable(False, False)
        self.create_widgets()
        self.focus_set()

    def focus_set(self):
        self.password_entry.focus_set()

    def create_widgets(self):
        self.password = tk.StringVar(self)

        content = ttk.Frame(self)
        header = ttk.Frame(content)
        title_label = None
        if self.master.platform.custom_titlebar:
            title_label = ttk.Label(header, style="Header.Title.TLabel",
                                    text=g_("Access denied"))
            self.bind_window_drag_handler(title_label)
        self.cancel_button = ttk.Button(
            header, style="Header.TButton", text=g_("Cancel"),
            command=self.destroy)
        self.ok_button = ttk.Button(
            header, style="Header.Suggested.TButton", text=g_("Continue"),
            command=self.on_ok)
        self.make_header(header, self.cancel_button, title_label,
                         self.ok_button, window_buttons=False)
        content.columnconfigure(1, weight=1)
        header.grid(column=0, row=0, columnspan=2, sticky=tk.W+tk.E)
        ttk.Label(content, text=g_("Video password:")).grid(
            row=1, column=0, sticky=tk.E, padx=PAD, pady=PAD)
        self.password_entry = ttk.Entry(content, textvariable=self.password)
        self.password_entry.bind("<Return>", self.on_enter_key_pressed)
        self.password_entry.grid(row=1, column=1, sticky=tk.W+tk.E, ipadx=PAD,
                                 ipady=PAD, padx=PAD, pady=PAD)
        content.pack(expand=1, fill=tk.BOTH)
        self.password.trace("w", self.on_password_changed)
        self.on_password_changed()

    def on_password_changed(self, *_):
        self.ok_button.state(
            ["!disabled" if self.password.get() else "disabled"])

    def on_enter_key_pressed(self, event):
        if self.password.get():
            self.on_ok()

    def on_ok(self):
        self.result = self.password.get()
        self.destroy()
