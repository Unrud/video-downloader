# resize_label.py
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
import tkinter.font
from tkinter import ttk


class ResizeLabel:
    def __init__(self, master=None, textvariable=None, text=None,
                 overflow=False, style=None):
        if textvariable is None:
            textvariable = tk.StringVar(master)
            if text:
                textvariable.set(text)
        self._textvariable = textvariable
        self._overflow = overflow
        self._frame = tk.Frame(master)
        self._frame.grid_propagate(0)
        self._frame.pack_propagate(0)
        self._label = ttk.Label(self._frame, style=style)
        self._frame.bind("<Configure>", self._on_configure)
        s = ttk.Style(master)
        relevant_styles = [".", "TLabel"]
        style_parts = style.split(".") if style else []
        for i in range(len(style_parts) - 1, -1, -1):
            relevant_styles.append(".".join(style_parts[i:]))
        font_name = "TkDefaultFont"
        borderwidth_dim = 0
        for style_name in relevant_styles:
            ss = s.configure(style_name) or {}
            font_name = ss.get("font", font_name)
            borderwidth_dim = ss.get("borderwidth", borderwidth_dim)
        self._font = tk.font.nametofont(font_name)
        self._borderwidth = round(self._frame.winfo_fpixels(borderwidth_dim))
        self._configured_size = None
        self._textvariable.trace("w", self._on_textvariable_changed)
        self.grid = self._frame.grid
        self.pack = self._frame.pack

    @property
    def text(self):
        return self._textvariable.get()

    @text.setter
    def text(self, value):
        return self._textvariable.set(value)

    def _on_textvariable_changed(self, *_):
        if self._configured_size is not None:
            self._on_configure(text_changed=True)

    def _on_configure(self, *_, text_changed=False):
        width, height = self._frame.winfo_width(), self._frame.winfo_height()
        if not text_changed and self._configured_size == (width, height):
            return
        text = self._textvariable.get()
        text_width = width - self._borderwidth * 2
        new_lines = []
        for _, line in enumerate(text.split("\n")):
            new_line = ""
            while line:
                test_new_line = new_line + line[0]
                if self._overflow:
                    test_new_line += "…"
                test_new_line += " "  # Add small puffer space
                if (not self._overflow and not new_line or
                        self._font.measure(test_new_line) <= text_width):
                    new_line += line[0]
                    line = line[1:]
                elif self._overflow:
                    new_line += "…"
                    line = ""
                else:
                    wrap_start = wrap_end = len(new_line)
                    space_pos = new_line.rfind(" ")
                    if space_pos >= 0:
                        wrap_start = space_pos
                        wrap_end = space_pos + 1
                    new_lines.append(new_line[:wrap_start])
                    new_line = new_line[wrap_end:]
            new_lines.append(new_line)
        text = "\n".join(new_lines)
        text_height = self._font.metrics("linespace") * len(new_lines) + 4
        height = text_height + self._borderwidth * 2
        self._label.configure(text=text)
        self._frame.configure(width=self._font.measure("…"), height=height)
        self._label.place(width=width, height=height)
        self._configured_size = (width, height)
