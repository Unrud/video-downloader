# Copyright (C) 2019-2020 Unrud <unrud@outlook.com>
#
# This file is part of Video Downloader.
#
# Video Downloader is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Video Downloader is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Video Downloader.  If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess

from gi.repository import GLib, GObject


def bind_property(obj_a, prop_a, obj_b=None, prop_b=None, func_a_to_b=None,
                  func_b_to_a=None, bi=False):
    if not func_a_to_b and not func_b_to_a:
        GObject.Binding.bind_property(
            obj_a, prop_a, obj_b, prop_b, GObject.BindingFlags.SYNC_CREATE | (
                GObject.BindingFlags.BIDIRECTIONAL if bi else
                GObject.BindingFlags.DEFAULT))
        return

    def apply_binding(reverse=False):
        nonlocal frozen
        if frozen:
            return
        if not reverse:
            value = obj_a.get_property(prop_a)
            if func_a_to_b:
                value = func_a_to_b(value)
            target_obj, target_prop = obj_b, prop_b
        else:
            value = obj_b.get_property(prop_b)
            if func_b_to_a:
                value = func_b_to_a(value)
            target_obj, target_prop = obj_a, prop_a
        if target_obj:
            frozen = True
            try:
                target_obj.set_property(target_prop, value)
            finally:
                frozen = False
    frozen = False
    apply_binding()
    obj_a.connect('notify::' + prop_a, lambda *_: apply_binding())
    if bi:
        obj_b.connect('notify::' + prop_b, lambda *_: apply_binding(True))


def expand_path(path):
    parts = path.replace(os.altsep or os.sep, os.sep).split(os.sep)
    home_dir = os.path.expanduser('~')
    if parts[0] == '~':
        parts[0] = home_dir
    elif parts[0].startswith('xdg-'):
        name = parts[0][len('xdg-'):].replace('-', '').upper()
        try:
            parts[0] = subprocess.check_output(
                ['xdg-user-dir', name], universal_newlines=True,
                stdin=subprocess.DEVNULL).splitlines()[0]
        except FileNotFoundError:
            parts[0] = home_dir
    return os.path.normpath(os.path.join(os.sep, *parts))


def g_log(domain, log_level, format_string, *args):
    fields = GLib.Variant('a{sv}', {
        'MESSAGE': GLib.Variant('s', format_string % args)})
    GLib.log_variant(domain, log_level, fields)
