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

import gettext
import os
import subprocess
import traceback
import typing

from gi.repository import Gio, GLib, GObject

from video_downloader import downloader
from video_downloader.downloader import MAX_RESOLUTION
from video_downloader.util import bind_property, expand_path, g_log

N_ = gettext.gettext


class Model(GObject.GObject, downloader.Handler):
    __gsignals__ = {
        'download-pulse': (GObject.SIGNAL_RUN_FIRST, None, ())
    }
    state = GObject.Property(type=str, default='start')
    prev_state = GObject.Property(type=str)
    mode = GObject.Property(type=str, default='audio')
    url = GObject.Property(type=str)
    error = GObject.Property(type=str)
    resolution = GObject.Property(type=GObject.TYPE_UINT, default=1080)
    download_dir = GObject.Property(type=str)
    download_dir_abs = GObject.Property(type=str)
    prefer_mpeg = GObject.Property(type=bool, default=False)
    download_playlist_index = GObject.Property(type=GObject.TYPE_INT64)
    download_playlist_count = GObject.Property(type=GObject.TYPE_INT64)
    download_filename = GObject.Property(type=str)
    download_title = GObject.Property(type=str)
    download_thumbnail = GObject.Property(type=str)
    # 0.0 - 1.0 (inclusive), negative if unknown:
    download_progress = GObject.Property(type=float, default=-1)
    download_bytes = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    download_bytes_total = GObject.Property(type=GObject.TYPE_INT64,
                                            default=-1)
    download_speed = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    download_eta = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    resolutions = [
        (MAX_RESOLUTION, N_('Best')),
        (4320, N_('4320p (8K)')),
        (2160, N_('2160p (4K)')),
        (1440, N_('1440p (HD)')),
        (1080, N_('1080p (HD)')),
        (720, N_('720p (HD)')),
        (480, N_('480p')),
        (360, N_('360p')),
        (240, N_('240p')),
        (144, N_('144p'))]

    def __init__(self, handler=None):
        super().__init__()
        self._handler = handler
        self._downloader = downloader.Downloader(self)
        self._download_finished_filenames = []
        self._filemanager_proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES |
            Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS |
            Gio.DBusProxyFlags.DO_NOT_AUTO_START_AT_CONSTRUCTION, None,
            'org.freedesktop.FileManager1', '/org/freedesktop/FileManager1',
            'org.freedesktop.FileManager1')
        bind_property(self, 'download-dir', self, 'download-dir-abs',
                      expand_path)
        self.actions = Gio.SimpleActionGroup.new()
        self.actions.add_action_entries([
            ('download', lambda *_: self.set_property('state', 'download')),
            ('cancel', lambda *_: self.set_property('state', 'cancel')),
            ('back', lambda *_: self.set_property('state', 'start')),
            ('open-download-dir', lambda *_: self.open_download_dir())])
        bind_property(self, 'url', self.actions.lookup_action('download'),
                      'enabled', bool)
        bind_property(self, 'state', self,
                      'prev-state', self._state_transition)
        bind_property(self, 'state', self.actions.lookup_action('cancel'),
                      'enabled', lambda s: s == 'download')

    def _state_transition(self, state):
        if state == 'start':
            assert self.prev_state != 'download'
        elif state == 'download':
            assert self.prev_state == 'start'
            self.error = ''
            self.download_playlist_index = 0
            self.download_playlist_count = 0
            self.download_filename = ''
            self.download_title = ''
            self.download_thumbnail = ''
            self.download_progress = -1
            self.download_bytes = -1
            self.download_bytes_total = -1
            self.download_speed = -1
            self.download_eta = -1
            self._download_finished_filenames.clear()
            self._downloader.start()
        elif state == 'cancel':
            assert self.prev_state == 'download'
            self._downloader.cancel()
        elif state in ['success', 'error']:
            assert self.prev_state == 'download'
        else:
            assert False
        return state

    def open_download_dir(self):
        if len(self._download_finished_filenames) == 1:
            method = 'ShowItems'
            paths = [os.path.join(self.download_dir_abs, filename) for
                     filename in self._download_finished_filenames]
        else:
            method = 'ShowFolders'
            paths = [self.download_dir_abs]
        parameters = GLib.Variant(
            '(ass)', ([Gio.File.new_for_path(p).get_uri() for p in paths], ''))
        try:
            self._filemanager_proxy.call_sync(
                method, parameters, Gio.DBusCallFlags.NONE, -1)
        except GLib.Error:
            g_log('youtube-dl', GLib.LogLevelFlags.LEVEL_WARNING, '%s',
                  traceback.format_exc())
            subprocess.run(['xdg-open', self.download_dir_abs], check=True)

    def shutdown(self):
        self._downloader.shutdown()

    def on_pulse(self):
        assert self.state in ['download', 'cancel']
        self.emit('download-pulse')

    def on_finished(self, success):
        assert self.state in ['download', 'cancel']
        if self.state == 'cancel':
            self.state = 'start'
        else:
            self.state = 'success' if success else 'error'

    def get_download_dir(self):
        assert self.state in ['download', 'cancel']
        return self.download_dir_abs

    def get_prefer_mpeg(self):
        assert self.state in ['download', 'cancel']
        return self.prefer_mpeg

    def get_url(self):
        assert self.state in ['download', 'cancel']
        return self.url

    def get_mode(self):
        assert self.state in ['download', 'cancel']
        return self.mode

    def get_resolution(self):
        assert self.state in ['download', 'cancel']
        return self.resolution

    def on_playlist_request(self):
        assert self.state in ['download', 'cancel']
        return self._handler.on_playlist_request()

    def on_login_request(self):
        assert self.state in ['download', 'cancel']
        return self._handler.on_login_request()

    def on_videopassword_request(self):
        assert self.state in ['download', 'cancel']
        return self._handler.on_videopassword_request()

    def on_error(self, msg):
        assert self.state in ['download', 'cancel']
        self.error = msg

    def on_load_progress(self, filename, progress, bytes_, bytes_total, eta,
                         speed):
        assert self.state in ['download', 'cancel']
        self.download_filename = filename
        self.download_progress = progress
        self.download_bytes = bytes_
        self.download_bytes_total = bytes_total
        self.download_eta = eta
        self.download_speed = speed

    def on_progress_start(self, playlist_index, playlist_count, title,
                          thumbnail):
        assert self.state in ['download', 'cancel']
        self.download_playlist_index = playlist_index
        self.download_playlist_count = playlist_count
        self.download_title = title
        self.download_thumbnail = thumbnail

    def on_progress_end(self, filename):
        assert self.state in ['download', 'cancel']
        self._download_finished_filenames.append(filename)


class Handler:
    def on_playlist_request(self) -> bool:
        raise NotImplementedError

    #                                          username password
    def on_login_request(self) -> typing.Tuple[str,     str]:
        raise NotImplementedError

    #                                     password
    def on_videopassword_request(self) -> str:
        raise NotImplementedError
