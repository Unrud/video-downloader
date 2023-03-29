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

import collections
import gettext
import os
import traceback
import typing

from gi.repository import Gio, GLib, GObject

from video_downloader import downloader
from video_downloader.downloader import MAX_RESOLUTION
from video_downloader.util import g_log, gobject_log, languages_from_locale
from video_downloader.util.connection import (CloseStack, PropertyBinding,
                                              SignalConnection)
from video_downloader.util.path import expand_path, open_in_file_manager
from video_downloader.util.response import AsyncResponse, Response

N_ = gettext.gettext


class Model(GObject.GObject, downloader.HandlerInterface):
    __gsignals__ = {
        'download-pulse': (GObject.SIGNAL_RUN_FIRST, None, ())
    }
    state = GObject.Property(type=str, default='start')
    mode = GObject.Property(type=str, default='audio')
    url = GObject.Property(type=str)
    error = GObject.Property(type=str)
    resolution = GObject.Property(type=GObject.TYPE_UINT, default=1080)
    download_folder = GObject.Property(type=str)
    # absolute path to dir of active/finished download (empty if no download)
    finished_download_dir = GObject.Property(type=str)
    # TYPE_STRV is None by default, empty list can be None or []
    finished_download_filenames = GObject.Property(type=GObject.TYPE_STRV)
    automatic_subtitles = GObject.Property(type=GObject.TYPE_STRV)
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
    resolutions = collections.OrderedDict([
        (MAX_RESOLUTION, N_('Best')),
        (4320, N_('4320p (8K)')),
        (2160, N_('2160p (4K)')),
        (1440, N_('1440p (HD)')),
        (1080, N_('1080p (HD)')),
        (720, N_('720p (HD)')),
        (480, N_('480p')),
        (360, N_('360p')),
        (240, N_('240p')),
        (144, N_('144p'))])

    _global_download_lock = set()

    def __init__(self, handler=None):
        super().__init__()
        self._cs = CloseStack()
        self._handler = handler
        self._cs.add_close_callback(setattr, self, '_handler', None)
        self._downloader = downloader.Downloader(self)
        self._cs.add_close_callback(self._downloader.shutdown)
        self._active_download_lock = None
        self.actions = gobject_log(Gio.SimpleActionGroup.new())
        for action_name, callback, *extra_args in [
                ('download', self.set_property, 'state', 'prepare'),
                ('cancel', self.set_property, 'state', 'cancel'),
                ('back', self.set_property, 'state', 'start'),
                ('open-finished-download-dir',
                 self._open_finished_download_dir)]:
            action = gobject_log(Gio.SimpleAction.new(action_name),
                                 action_name)
            self._cs.push(SignalConnection(
                action, 'activate', callback, *extra_args, no_args=True))
            self.actions.add_action(action)
        self._cs.push(PropertyBinding(
            self, 'url', self.actions.lookup_action('download'), 'enabled',
            bool))
        self._prev_state = None
        self._cs.push(PropertyBinding(
            self, 'state', func_a_to_b=self._state_transition))
        self._cs.push(PropertyBinding(
            self, 'state', self.actions.lookup_action('cancel'), 'enabled',
            lambda s: s == 'download'))
        self._cs.push(PropertyBinding(
            self, 'state',
            self.actions.lookup_action('open-finished-download-dir'),
            'enabled', lambda s: s == 'success'))

    def _state_transition(self, state):
        if state == 'start':
            assert self._prev_state != 'download'
        elif state == 'prepare':
            assert self._prev_state == 'start'
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
            self.finished_download_filenames = []
            self.finished_download_dir = ''
            self._try_start_download()
        elif state == 'download':
            assert self._prev_state == 'prepare'
            self._downloader.start()
        elif state == 'cancel':
            assert self._prev_state == 'download'
            self._downloader.cancel()
        elif state in ['success', 'error']:
            assert self._prev_state == 'download'
        else:
            assert False, 'invalid value for \'state\' property: %r' % state
        self._prev_state = state

    def _open_finished_download_dir(self):
        assert self.finished_download_dir
        open_in_file_manager(self.finished_download_dir,
                             self.finished_download_filenames)

    def _try_start_download(self):
        path = expand_path(self.download_folder)
        message = check_download_dir(path, create=True)
        if message is None:
            self.finished_download_dir = path
            self.state = 'download'
            return
        response = self._handler.on_download_folder_error(
            N_('Invalid download folder'), message, path)

        def handle_response(response):
            if response.cancelled:
                self.state = 'start'
            else:
                self._try_start_download()
        response.add_done_callback(handle_response)

    def shutdown(self):
        self._cs.close()

    def on_pulse(self):
        assert self.state in ['download', 'cancel']
        self.emit('download-pulse')

    def on_finished(self, success):
        assert self.state in ['download', 'cancel']
        self._download_unlock()
        if self.state == 'cancel':
            self.state = 'start'
        else:
            self.state = 'success' if success else 'error'

    def get_download_dir(self):
        assert self.state in ['download', 'cancel']
        return self.finished_download_dir

    def get_prefer_mpeg(self):
        assert self.state in ['download', 'cancel']
        return self.prefer_mpeg

    def get_automatic_subtitles(self):
        assert self.state in ['download', 'cancel']
        return [*languages_from_locale(), *(self.automatic_subtitles or [])]

    def get_url(self):
        assert self.state in ['download', 'cancel']
        return self.url

    def get_mode(self):
        assert self.state in ['download', 'cancel']
        return self.mode

    def get_resolution(self):
        assert self.state in ['download', 'cancel']
        return self.resolution

    def _forward_response(self, response):
        def callback(response):
            if response.cancelled:
                self.state = 'cancel'
        if isinstance(response, AsyncResponse):
            response.add_done_callback(callback)
            if self.state == 'cancel':
                response.cancel()
        return response

    def on_playlist_request(self):
        assert self.state in ['download', 'cancel']
        return self._forward_response(self._handler.on_playlist_request())

    def on_login_request(self):
        assert self.state in ['download', 'cancel']
        return self._forward_response(self._handler.on_login_request())

    def on_password_request(self):
        assert self.state in ['download', 'cancel']
        return self._forward_response(self._handler.on_password_request())

    def on_error(self, msg):
        assert self.state in ['download', 'cancel']
        self.error = msg

    def on_progress(self, filename, progress, bytes_, bytes_total, eta, speed):
        assert self.state in ['download', 'cancel']
        self.download_filename = filename
        self.download_progress = progress
        self.download_bytes = bytes_
        self.download_bytes_total = bytes_total
        self.download_eta = eta
        self.download_speed = speed

    def on_download_start(self, playlist_index, playlist_count, title):
        assert self.state in ['download', 'cancel']
        self.download_playlist_index = playlist_index
        self.download_playlist_count = playlist_count
        self.download_title = title

    def _download_unlock(self):
        if self._active_download_lock:
            self._global_download_lock.remove(self._active_download_lock)
            self._active_download_lock = None

    def on_download_lock(self, name):
        assert self.state in ['download', 'cancel']
        assert self._active_download_lock is None
        if name in self._global_download_lock:
            return False
        self._global_download_lock.add(name)
        self._active_download_lock = name
        return True

    def on_download_thumbnail(self, thumbnail):
        assert self.state in ['download', 'cancel']
        self.download_thumbnail = thumbnail

    def on_download_finished(self, filename):
        assert self.state in ['download', 'cancel']
        self._download_unlock()
        self.finished_download_filenames = [
            *(self.finished_download_filenames or []), filename]


def check_download_dir(path: str, create: bool = False
                       ) -> typing.Optional[str]:
    if create:
        try:
            os.makedirs(path, exist_ok=True)
        except FileExistsError:
            return N_('Not a directory')
        except Exception:
            g_log(None, GLib.LogLevelFlags.LEVEL_DEBUG,
                  '%s', traceback.format_exc())
            return N_('Permission denied')
    elif not os.path.isdir(path):
        return N_('Not a directory')
    if not os.access(path, os.R_OK | os.W_OK | os.X_OK,
                     effective_ids=os.access in os.supports_effective_ids):
        return N_('Permission denied')
    return None


class HandlerInterface:
    def on_playlist_request(self) -> Response[bool]:
        raise NotImplementedError

    #                                                   user password
    def on_login_request(self) -> Response[typing.Tuple[str, str]]:
        raise NotImplementedError

    #                                         password
    def on_password_request(self) -> Response[str]:
        raise NotImplementedError

    def on_download_folder_error(self, title: str, message: str
                                 ) -> Response[None]:
        raise NotImplementedError
