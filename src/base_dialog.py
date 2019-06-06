# base_dialog.py
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

from video_downloader.base_window_mixin import BaseWindowMixin


class BaseDialog(BaseWindowMixin, tk.Toplevel):
    def __init__(self, master=None):
        tk.Toplevel.__init__(self, master)
        BaseWindowMixin.__init__(self, self.master.platform)
        self.result = None
        self.transient(self.master)
        self.grab_set()

    def wait(self):
        self.wait_window(self)
        return self.result
