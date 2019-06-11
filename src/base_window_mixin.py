# base_window_mixin.py
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

import tkinter as tk
from tkinter import ttk

from video_downloader import PAD


class BaseWindowMixin:
    def __init__(self, platform):
        self.platform = platform
        self.platform.window_apply(self)
        self.window_drag_pos = None

    def bind_window_drag_handler(self, widget):
        if self.platform.custom_titlebar:
            widget.bind("<ButtonPress-1>", self.on_window_drag_start)
            widget.bind("<ButtonRelease-1>", self.on_window_drag_stop)
            widget.bind("<B1-Motion>", self.on_window_drag_motion)

    def make_header(self, header_frame, left_widget=None, center_widget=None,
                    right_widget=None, window_buttons=True):
        if left_widget is None:
            left_widget = ttk.Frame(header_frame, style="Header.TFrame")
            self.bind_window_drag_handler(left_widget)
        if center_widget is None:
            center_widget = ttk.Frame(header_frame, style="Header.TFrame")
            self.bind_window_drag_handler(center_widget)
        if right_widget is None:
            right_widget = ttk.Frame(header_frame, style="Header.TFrame")
            self.bind_window_drag_handler(right_widget)
        header_frame.config(style="Header.TFrame")
        header_frame.columnconfigure(0, weight=1)
        left_widget.grid(row=0, column=0, in_=header_frame, pady=PAD,
                         padx=PAD, sticky=tk.W)
        header_frame.columnconfigure(1, weight=1)
        center_widget.grid(row=0, column=1, in_=header_frame, pady=PAD,
                           padx=PAD)
        header_frame.columnconfigure(2, weight=1)
        right_widget.grid(row=0, column=2, in_=header_frame, pady=PAD,
                          padx=PAD, sticky=tk.E)
        self.bind_window_drag_handler(header_frame)
        if window_buttons and self.platform.custom_titlebar:
            min_button = ttk.Button(
                header_frame, style="Header.WindowButton.TButton", text="➖",
                command=self.iconify, width=4, takefocus=False)
            close_button = ttk.Button(
                header_frame, style="Header.WindowButton.TButton", text="✖",
                command=self.quit, width=4, takefocus=False)
            min_button.grid(column=3, row=0, sticky=tk.E+tk.N+tk.S)
            close_button.grid(column=4, row=0, sticky=tk.E+tk.N+tk.S)

    def on_window_drag_start(self, event):
        self.window_drag_pos = (event.x, event.y)

    def on_window_drag_stop(self, event):
        self.window_drag_pos = None

    def on_window_drag_motion(self, event):
        if self.window_drag_pos is None:
            return
        deltax = event.x - self.window_drag_pos[0]
        deltay = event.y - self.window_drag_pos[1]
        x = self.winfo_rootx() + deltax
        y = self.winfo_rooty() + deltay
        self.geometry("+%s+%s" % (x, y))
