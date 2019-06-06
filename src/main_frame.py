# main_frame.py
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

g_ = gettext.gettext


class MainFrame(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.active_mode = None
        self.create_widgets()

    def focus_set(self, initial=True):
        _, _, entry = self.modes[self.active_mode]
        entry.focus_set()
        if initial:
            entry.icursor(0)
            entry.event_generate("<<SelectAll>>")
        else:
            entry.select_clear()
            entry.icursor(tk.END)

    def on_url_changed(self, *_):
        self.downloadButton.state(
            ["!disabled" if self.master.model.url.get() else "disabled"])

    def on_mode_changed(self, *_):
        for button, _, _ in self.modes.values():
            button.state(["!pressed"])
        button, _, _ = self.modes[self.master.model.mode.get()]
        button.state(["pressed"])
        if self.active_mode == self.master.model.mode.get():
            self.focus_set(initial=False)
            return
        self.active_mode = self.master.model.mode.get()
        for _, frame, _ in self.modes.values():
            frame.pack_forget()
        _, frame, _ = self.modes[self.active_mode]
        frame.pack(expand=1, fill=tk.BOTH)
        self.focus_set(initial=False)

    def on_resolution_changed(self, *_):
        resolution_name, _ = self.master.model.resolutions[
            self.master.model.resolutionIndex.get()]
        self.resolution_name.set(resolution_name)

    def on_audio(self):
        self.master.model.mode.set("audio")

    def on_video(self):
        self.master.model.mode.set("video")

    def on_enter_key_pressed(self, event):
        if self.master.model.url.get():
            self.master.model.start()

    def create_widgets(self):
        self.resolution_name = tk.StringVar(self.master)

        header = ttk.Frame(self)
        inner_header_frame = ttk.Frame(header, style="Header.TFrame")
        self.audio_button = ttk.Button(
            inner_header_frame, style="Header.TButton", text=g_("Audio"),
            command=self.on_audio)
        self.video_button = ttk.Button(
            inner_header_frame, style="Header.TButton", text=g_("Video"),
            command=self.on_video)
        self.audio_button.pack(fill=tk.Y, side=tk.LEFT)
        self.video_button.pack(fill=tk.Y, side=tk.LEFT)
        self.downloadButton = ttk.Button(
            header, style="Header.Suggested.TButton", text=g_("Download"),
            command=self.master.model.start)
        self.master.make_header(header, None, inner_header_frame,
                                self.downloadButton)
        header.pack(fill=tk.X, side=tk.TOP)
        self.audio_frame = ttk.Frame(self)
        self.audio_frame.columnconfigure(1, weight=1)
        self.video_frame = ttk.Frame(self)
        self.video_frame.columnconfigure(1, weight=1)
        ttk.Label(self.audio_frame, text=g_("URL:")).grid(
            row=0, column=0, sticky=tk.E, padx=PAD, pady=PAD)
        self.audio_url_entry = ttk.Entry(
            self.audio_frame, textvariable=self.master.model.url)
        self.audio_url_entry.bind("<Return>", self.on_enter_key_pressed)
        self.audio_url_entry.grid(row=0, column=1, sticky=tk.W+tk.E, ipadx=PAD,
                                  ipady=PAD, padx=PAD, pady=PAD)
        ttk.Label(self.video_frame, text=g_("URL:")).grid(
            row=0, column=0, sticky=tk.E, padx=PAD, pady=PAD)
        ttk.Label(self.video_frame, text=g_("Resolution:")).grid(
            row=1, column=0, sticky=tk.E, padx=PAD, pady=PAD)
        self.video_url_entry = ttk.Entry(
            self.video_frame, textvariable=self.master.model.url)
        self.video_url_entry.bind("<Return>", self.on_enter_key_pressed)
        self.video_url_entry.grid(row=0, column=1, sticky=tk.W+tk.E, ipadx=PAD,
                                  ipady=PAD, padx=PAD, pady=PAD)
        self.resolution_menu = tk.Menu(self.master, tearoff=0)
        for i, (resolution_name, _) in enumerate(
                self.master.model.resolutions):

            def on_resolution(i=i):
                self.master.model.resolutionIndex.set(i)
            self.resolution_menu.add_command(
                label=resolution_name, command=on_resolution)
        self.resolution_menubutton = ttk.Menubutton(
            self.video_frame, direction="below", width=20,
            menu=self.resolution_menu,
            textvariable=self.resolution_name)
        self.resolution_menubutton.grid(row=1, column=1, sticky=tk.W, padx=PAD,
                                        pady=PAD)
        self.modes = {
            "audio": (self.audio_button, self.audio_frame,
                      self.audio_url_entry),
            "video": (self.video_button, self.video_frame,
                      self.video_url_entry)}
        self.master.model.url.trace("w", self.on_url_changed)
        self.master.model.mode.trace("w", self.on_mode_changed)
        self.master.model.resolutionIndex.trace(
            "w", self.on_resolution_changed)
        self.on_url_changed()
        self.on_mode_changed()
        self.on_resolution_changed()
