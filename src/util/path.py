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
import sys
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


def encode_filesystem_path(path):
    return path.encode(sys.getfilesystemencoding(),
                       sys.getfilesystemencodeerrors())


def decode_filesystem_path(path):
    return path.decode(sys.getfilesystemencoding(),
                       sys.getfilesystemencodeerrors())


def open_in_file_manager(directory, filenames):
    # org.freedesktop.portal.Documents
    portal_documents_proxy = gobject_log(Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES |
        Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS |
        Gio.DBusProxyFlags.DO_NOT_AUTO_START_AT_CONSTRUCTION, None,
        'org.freedesktop.portal.Documents',
        '/org/freedesktop/portal/documents',
        'org.freedesktop.portal.Documents'))
    try:
        documents_mount_point = decode_filesystem_path(
            portal_documents_proxy.call_sync(
                'GetMountPoint', None, Gio.DBusCallFlags.NONE, -1
            ).get_child_value(0).get_bytestring())
    except GLib.Error:
        g_log(None, GLib.LogLevelFlags.LEVEL_WARNING, '%s',
              traceback.format_exc())
    else:
        directory_in_documents_portal = os.path.normpath(directory).startswith(
            os.path.normpath(documents_mount_point)+os.sep)
        if directory_in_documents_portal:
            # WORAROUND: Subpaths in the documents portal are not translated
            filenames = []

    # org.freedesktop.portal.OpenURI
    portal_open_uri_proxy = gobject_log(Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES |
        Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS |
        Gio.DBusProxyFlags.DO_NOT_AUTO_START_AT_CONSTRUCTION, None,
        'org.freedesktop.portal.Desktop',
        '/org/freedesktop/portal/desktop',
        'org.freedesktop.portal.OpenURI'))
    fdlist = gobject_log(Gio.UnixFDList())
    for filename in filenames:
        path = os.path.join(directory, filename)
        try:
            fd = os.open(path, os.O_RDONLY)
        except OSError:
            g_log(None, GLib.LogLevelFlags.LEVEL_DEBUG, '%s',
                  traceback.format_exc())
            continue
        break
    else:
        path = directory
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
    method = 'ShowFolders' if path == directory else 'ShowItems'
    parameters = GLib.Variant(
        '(ass)', ([Gio.File.new_for_path(path).get_uri()], ''))
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
