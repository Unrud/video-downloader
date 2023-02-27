# Copyright (C) 2019-2021 Unrud <unrud@outlook.com>
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
import traceback

from gi.repository import Gio, GLib

from video_downloader.util import g_log, gobject_log


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


def open_in_file_manager(directory, filenames):
    # org.freedesktop.portal.OpenURI
    portal_open_uri_proxy = gobject_log(Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES |
        Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS |
        Gio.DBusProxyFlags.DO_NOT_AUTO_START_AT_CONSTRUCTION, None,
        'org.freedesktop.portal.Desktop',
        '/org/freedesktop/portal/desktop',
        'org.freedesktop.portal.OpenURI'))
    fdlist = gobject_log(Gio.UnixFDList())
    path = directory
    if filenames:
        path = os.path.join(path, filenames[0])
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        g_log(None, GLib.LogLevelFlags.LEVEL_WARNING, '%s',
              traceback.format_exc())
        return
    try:
        handle = fdlist.append(fd)
    finally:
        os.close(fd)
    try:
        parameters = GLib.Variant('(sha{sv})', ('', handle, {}))
        portal_open_uri_proxy.call_with_unix_fd_list_sync(
            'OpenDirectory', parameters, Gio.DBusCallFlags.NONE, -1, fdlist)
    except GLib.Error:
        g_log(None, GLib.LogLevelFlags.LEVEL_WARNING, '%s',
              traceback.format_exc())
    else:
        return

    # org.freedesktop.FileManager1
    filemanager_proxy = gobject_log(Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES |
        Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS |
        Gio.DBusProxyFlags.DO_NOT_AUTO_START_AT_CONSTRUCTION, None,
        'org.freedesktop.FileManager1', '/org/freedesktop/FileManager1',
        'org.freedesktop.FileManager1'))
    if filenames:
        method = 'ShowItems'
        paths = [os.path.join(directory, filename)
                 for filename in (filenames or [])]
        paths = paths[:1]  # Multiple paths open multiple windows
    else:
        method = 'ShowFolders'
        paths = [directory]
    parameters = GLib.Variant(
        '(ass)', ([Gio.File.new_for_path(p).get_uri() for p in paths], ''))
    try:
        filemanager_proxy.call_sync(
            method, parameters, Gio.DBusCallFlags.NONE, -1)
    except GLib.Error:
        g_log(None, GLib.LogLevelFlags.LEVEL_WARNING, '%s',
              traceback.format_exc())
    else:
        return

    # xdg-open
    try:
        subprocess.run(['xdg-open', directory], check=True)
    except subprocess.SubprocessError:
        g_log(None, GLib.LogLevelFlags.LEVEL_WARNING, '%s',
              traceback.format_exc())
    else:
        return
