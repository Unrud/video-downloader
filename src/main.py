# main.py
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

import argparse
import contextlib
import gettext
import tkinter as tk
import tkinter.font
from tkinter import ttk

from video_downloader.base_window_mixin import BaseWindowMixin
from video_downloader.download_frame import DownloadFrame
from video_downloader.error_frame import ErrorFrame
from video_downloader.login_dialog import LoginDialog
from video_downloader.main_frame import MainFrame
from video_downloader.model import Handler, Model
from video_downloader.platform import Platform
from video_downloader.playlist_dialog import PlaylistDialog
from video_downloader.success_frame import SuccessFrame
from video_downloader.videopassword_dialog import VideopasswordDialog

g_ = gettext.gettext


class App(BaseWindowMixin, tk.Tk, Handler):
    def __init__(self):
        tk.Tk.__init__(self)
        # BUG: Fonts don't work, when they are not created here.
        f1 = tk.font.Font(self)
        f2 = tk.font.Font(self)
        BaseWindowMixin.__init__(self, Platform(self, [f1, f2]))
        self.active_page = None
        self.minsize(self.pt_to_px(480), self.pt_to_px(180))
        self.resizable(False, False)
        self.title(g_("Video Downloader"))
        self.model = Model(self, self)
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.create_widgets()

    def quit(self):
        with contextlib.suppress(AssertionError):
            self.model.cancel()
        super().quit()

    def focus_set(self):
        self.pages[self.active_page].focus_set()

    def create_widgets(self):
        self.bind_class("TEntry", "<<ContextMenu>>", self.show_context_menu)
        # HACK: Fix select all
        self.bind_class("TEntry", "<<SelectAll>>", lambda event: (
            self.after_idle(event.widget.select_range, 0, tk.END)))
        self.bind_class("TEntry", "<<SelectAll>>", lambda event: (
            self.after_idle(event.widget.select_range, 0, tk.END)))
        self.bind_class("TEntry", "<Control-Key-a>", lambda event: (
            event.widget.event_generate("<<SelectAll>>")))
        self.bind_class("TEntry", "<Control-Key-A>", lambda event: (
            event.widget.event_generate("<<SelectAll>>")))
        self.main_frame = MainFrame(self)
        self.download_frame = DownloadFrame(self)
        self.error_frame = ErrorFrame(self)
        self.success_frame = SuccessFrame(self)
        self.model.page.trace("w", self.on_page_changed)
        self.pages = {
            "main": self.main_frame,
            "download": self.download_frame,
            "error": self.error_frame,
            "success": self.success_frame}
        self.on_page_changed()

    def on_playlist_request(self):
        result = PlaylistDialog(self).wait()
        if result is None:
            self.model.cancel()
            return False
        return result

    def on_login_request(self):
        result = LoginDialog(self).wait()
        if result is None:
            self.model.cancel()
            return ("", "")
        return result

    def on_videopassword_request(self):
        result = VideopasswordDialog(self).wait()
        if result is None:
            self.model.cancel()
            return ""
        return result

    def on_page_changed(self, *_):
        if self.active_page == self.model.page.get():
            return
        self.active_page = self.model.page.get()
        for frame in self.pages.values():
            frame.pack_forget()
        self.pages[self.active_page].pack(expand=1, fill=tk.BOTH)
        self.focus_set()

    def show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=g_("Cut"))
        menu.add_command(label=g_("Copy"))
        menu.add_command(label=g_("Paste"))
        widget = event.widget
        select = widget.select_present()
        menu.entryconfig(0, state=tk.NORMAL if select else tk.DISABLED,
                         command=lambda: widget.event_generate("<<Cut>>"))
        menu.entryconfig(1, state=tk.NORMAL if select else tk.DISABLED,
                         command=lambda: widget.event_generate("<<Copy>>"))
        menu.entryconfig(2, command=lambda: widget.event_generate("<<Paste>>"))
        self.tk.call("tk_popup", menu, event.x_root, event.y_root)


def main(version):
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=version)
    parser.parse_args()
    app = App()
    app.mainloop()
