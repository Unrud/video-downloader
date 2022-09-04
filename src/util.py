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

import locale
import os
import subprocess

from gi.repository import GLib, GObject


class ConnectionManager:
    def __init__(self):
        self.__connections = []

    def bind(self, *args, **kwargs):
        self.__connections.append(PropertyBinding(*args, **kwargs))

    def connect(self, *args, **kwargs):
        self.__connections.append(SignalConnection(*args, **kwargs))

    def disconnect(self):
        while self.__connections:
            self.__connections[-1].disconnect()
            del self.__connections[-1]

    def __del__(self):
        self.disconnect()


class SignalConnection:
    def __init__(self, obj, signal_name, callback, *extra_args, no_args=False):
        self.__obj = obj
        self.__callback = callback
        self.__extra_args = extra_args
        self.__no_args = no_args
        self.__handler = None
        try:
            self.__handler = obj.connect(signal_name, self.__on_notify)
        except BaseException:
            self.disconnect()

    def __on_notify(self, *args):
        if self.__no_args:
            args = []
        self.__callback(*args, *self.__extra_args)

    def disconnect(self):
        if self.__handler is not None:
            self.__obj.disconnect(self.__handler)
        self.__obj = self.__handler = self.__callback = self.__extra_args = (
            None)


class PropertyBinding:
    def __init__(self, obj_a, prop_a, obj_b=None, prop_b=None,
                 func_a_to_b=None, func_b_to_a=None, bi=False):
        self.__binding = None
        self.__frozen = False
        self.__connections = []
        try:
            if not func_a_to_b and not func_b_to_a:
                self.__binding = GObject.Binding.bind_property(
                    obj_a, prop_a, obj_b, prop_b,
                    GObject.BindingFlags.SYNC_CREATE | (
                        GObject.BindingFlags.BIDIRECTIONAL if bi else
                        GObject.BindingFlags.DEFAULT))
                return
            self.__connections.append(SignalConnection(
                obj_a, 'notify::' + prop_a, self.__apply,
                obj_a, prop_a, obj_b, prop_b, func_a_to_b, no_args=True))
            if bi:
                self.__connections.append(SignalConnection(
                    obj_b, 'notify::' + prop_b, self.__apply,
                    obj_b, prop_b, obj_a, prop_a, func_b_to_a, no_args=True))
        except BaseException:
            self.disconnect()
            raise
        self.__apply(obj_a, prop_a, obj_b, prop_b, func_a_to_b)

    def __apply(self, src_obj, src_prop, dest_obj, dest_prop, to_func):
        if self.__frozen:
            return
        value = src_obj.get_property(src_prop)
        if to_func:
            value = to_func(value)
        if dest_obj and value is not None:
            self.__frozen = True
            try:
                dest_obj.set_property(dest_prop, value)
            finally:
                self.__frozen = False

    def disconnect(self):
        if self.__binding is not None:
            self.__binding.unbind()
        self.__binding = None
        while self.__connections:
            self.__connections[-1].disconnect()
            del self.__connections[-1]


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


def gobject_log(obj, info=None):
    DOMAIN = 'gobject-ref'
    LEVEL = GLib.LogLevelFlags.LEVEL_DEBUG
    name = repr(obj)
    if info:
        name += ' (' + str(info) + ')'
    g_log(DOMAIN, LEVEL, 'Create %s', name)
    obj.weak_ref(g_log, DOMAIN, LEVEL, 'Destroy %s', name)
    return obj


def g_log(domain, log_level, format_string, *args):
    fields = GLib.Variant('a{sv}', {
        'MESSAGE': GLib.Variant('s', format_string % args)})
    GLib.log_variant(domain, log_level, fields)


def languages_from_locale():
    locale_languages = []
    for envar in ['LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG']:
        val = os.environ.get(envar)
        if val:
            locale_languages.extend(val.split(':'))
            break
    if 'C' not in locale_languages:
        locale_languages.append('C')
    languages = []
    for lang in locale_languages:
        lang = locale.normalize(lang)
        for sep in ['@', '.', '_']:
            lang = lang.split(sep, maxsplit=1)[0]
        if lang == 'C':
            lang = 'en'
        if lang not in languages:
            languages.append(lang)
    return languages
