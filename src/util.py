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

import functools
import locale
import os
import subprocess
import traceback
import typing
from collections import OrderedDict

from gi.repository import GLib, GObject


class Closable:
    def __init__(self):
        self.__closed = False
        self.__close_callbacks = []

    @property
    def closed(self):
        return self.__closed

    def add_close_callback(self, callback, *args, **kwargs):
        self.__close_callbacks.append(
            functools.partial(callback, *args, **kwargs))
        if self.closed:
            self.close()

    def close(self):
        self.__closed = True
        while self.__close_callbacks:
            try:
                self.__close_callbacks[-1]()
            except Exception:
                g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                      '%s', traceback.format_exc())
            del self.__close_callbacks[-1]

    def __del__(self):
        self.close()


class CloseStack(Closable):
    def __init__(self):
        super().__init__()
        self.__key = 0
        self.__closables = OrderedDict()

    def push(self, closable):
        assert not self.closed, 'closed'
        self.__closables[self.__key] = closable
        closable.add_close_callback(self.__closables.pop, self.__key)
        self.__key += 1

    def close(self):
        while self.__closables:
            key = next(reversed(self.__closables))
            self.__closables[key].close()
        super().close()


class SignalConnection(Closable):
    def __init__(self, obj, signal_name, callback, *extra_args, no_args=False):
        super().__init__()

        def on_notify(*args):
            if no_args:
                args = []
            callback(*args, *extra_args)
        handler = obj.connect(signal_name, on_notify)
        self.add_close_callback(obj.disconnect, handler)


class PropertyBinding(Closable):
    def __init__(self, obj_a, prop_a, obj_b=None, prop_b=None,
                 func_a_to_b=None, func_b_to_a=None, bi=False):
        super().__init__()
        self.__frozen = False

        if not func_a_to_b and not func_b_to_a:
            binding = GObject.Binding.bind_property(
                obj_a, prop_a, obj_b, prop_b,
                GObject.BindingFlags.SYNC_CREATE | (
                    GObject.BindingFlags.BIDIRECTIONAL if bi else
                    GObject.BindingFlags.DEFAULT))
            self.add_close_callback(binding.unbind)
            return

        try:
            connection_a_to_b = SignalConnection(
                obj_a, 'notify::' + prop_a, self.__apply,
                obj_a, prop_a, obj_b, prop_b, func_a_to_b, no_args=True)
            self.add_close_callback(connection_a_to_b.close)
            if bi:
                connection_b_to_a = SignalConnection(
                    obj_b, 'notify::' + prop_b, self.__apply,
                    obj_b, prop_b, obj_a, prop_a, func_b_to_a, no_args=True)
                self.add_close_callback(connection_b_to_a.close)
        except BaseException:
            self.close()
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


_R = typing.TypeVar('R')


class AsyncResponse(typing.Generic[_R], Closable):
    def __init__(self) -> None:
        super().__init__()
        self.__done = False
        self.__cancelled = False
        self.__result = None

    @property
    def done(self) -> bool:
        return self.__done

    @property
    def cancelled(self) -> bool:
        return self.__cancelled

    @property
    def result(self) -> typing.Optional[_R]:
        return self.__result

    def add_done_callback(self, callback: typing.Callable[
                              ["AsyncResponse[_R]"], None]) -> None:
        self.add_close_callback(callback, self)

    def set_result(self, result: _R) -> None:
        assert not self.done, 'done'
        self.__result = result
        self.__done = True
        self.close()

    def cancel(self) -> None:
        assert not self.done, 'done'
        self.close()

    def chain(self, chained_response: "AsyncResponse[_R]"
              ) -> "AsyncResponse[_R]":
        def callbackChain(response):
            assert response.done
            if not response.cancelled:
                chained_response.set_result(response.result)
            elif not chained_response.cancelled:
                chained_response.cancel()
        self.add_done_callback(callbackChain)

        def callbackCancel(chained_response):
            assert chained_response.done
            if not self.done:
                assert chained_response.cancelled
                self.cancel()
        chained_response.add_done_callback(callbackCancel)

    def close(self):
        if not self.done:
            self.__cancelled = True
            self.__done = True
        super().close()


Response = typing.Union[_R, AsyncResponse[_R]]
