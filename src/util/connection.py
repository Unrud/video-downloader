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
import math
import time
import traceback
from collections import OrderedDict

from gi.repository import Gio, GLib, GObject

from video_downloader.util import g_log, gobject_log


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
        return closable

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
            return callback(*args, *extra_args)
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


class RateLimit(Closable):
    def __init__(self, func, seconds=0):
        super().__init__()
        self.__seconds = seconds
        self.__func = func
        self.__last_call = 0
        self.__timeout = None

        def cleanup_timeout():
            if self.__timeout is None:
                return
            GLib.Source.remove(self.__timeout)
            self.__timeout = None
        self.add_close_callback(cleanup_timeout)

    def __call__(self):
        if self.__timeout is not None or self.closed:
            return
        timeout = max(self.__seconds - (time.monotonic() - self.__last_call),
                      0)
        self.__timeout = GLib.timeout_add(
            math.ceil(timeout * 1000), self.__handle_timeout)

    def __handle_timeout(self):
        self.__func()
        self.__last_call = time.monotonic()
        self.__timeout = None
        return False


def create_action(action_group, closable, name, callback, *extra_args,
                  parameter_type=None, no_args=False):
    action = gobject_log(Gio.SimpleAction.new(name, parameter_type), name)
    closable.push(SignalConnection(
        action, 'activate', callback, *extra_args, no_args=no_args))
    action_group.add_action(action)
    closable.add_close_callback(action_group.remove_action, name)
