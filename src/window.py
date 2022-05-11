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
import locale
import math
import os
import uuid

from gi.repository import GdkPixbuf, Gio, GLib, Gtk, Handy

from video_downloader.about_dialog import AboutDialog
from video_downloader.authentication_dialog import LoginDialog, PasswordDialog
from video_downloader.model import Handler, Model
from video_downloader.playlist_dialog import PlaylistDialog
from video_downloader.util import bind_property, g_log

DOWNLOAD_IMAGE_SIZE = 128
MAX_ASPECT_RATIO = 2.39
N_ = gettext.gettext

NOTIFICATION_ACTIONS = (
    'notification-success', 'notification-open-download-dir',
    'notification-error')


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/window.ui')
class Window(Handy.ApplicationWindow, Handler):
    __gtype_name__ = 'VideoDownloaderWindow'
    error_buffer = Gtk.Template.Child()
    resolutions_store = Gtk.Template.Child()
    audio_url_wdg = Gtk.Template.Child()
    video_url_wdg = Gtk.Template.Child()
    resolution_wdg = Gtk.Template.Child()
    main_stack_wdg = Gtk.Template.Child()
    audio_video_stack_wdg = Gtk.Template.Child()
    audio_download_wdg = Gtk.Template.Child()
    video_download_wdg = Gtk.Template.Child()
    error_back_wdg = Gtk.Template.Child()
    success_back_wdg = Gtk.Template.Child()
    download_cancel_wdg = Gtk.Template.Child()
    open_download_dir_wdg = Gtk.Template.Child()
    download_page_title_wdg = Gtk.Template.Child()
    download_title_wdg = Gtk.Template.Child()
    download_progress_wdg = Gtk.Template.Child()
    download_info_wdg = Gtk.Template.Child()
    download_images_wdg = Gtk.Template.Child()
    color_system_wdg = Gtk.Template.Child()
    color_light_wdg = Gtk.Template.Child()
    color_dark_wdg = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)
        self.uuid = str(uuid.uuid4())  # Id for matching notifications
        self.model = model = Model(self)
        # Setup actions
        for name in model.actions.list_actions():
            self.add_action(model.actions.lookup_action(name))
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', lambda *_: self._show_about_dialog())
        self.add_action(about_action)
        # Bind properties to UI
        bind_property(model, 'error', self.error_buffer, 'text')
        bind_property(model, 'url', self.audio_url_wdg, 'text', bi=True)
        bind_property(model, 'url', self.video_url_wdg, 'text', bi=True)
        for resolution, description in model.resolutions:
            it = self.resolutions_store.append()
            self.resolutions_store.set(it, 0, str(resolution), 1, description)
        bind_property(model, 'resolution', self.resolution_wdg, 'active-id',
                      str, int, bi=True)
        bind_property(
            model, 'state', self.main_stack_wdg, 'visible-child-name',
            func_a_to_b=lambda s: {'cancel': 'download'}.get(s, s))
        bind_property(model, 'state', func_a_to_b=self._update_notification)
        bind_property(model, 'mode', self.audio_video_stack_wdg,
                      'visible-child-name', bi=True)
        bind_property(self.main_stack_wdg, 'visible-child-name',
                      func_a_to_b=self._update_focus_and_default)
        bind_property(self.audio_video_stack_wdg, 'visible-child-name',
                      func_a_to_b=self._update_focus_and_default)
        bind_property(model, 'download-dir-abs',
                      func_a_to_b=self._update_open_download_dir_wdg_tooltip)
        for name in ['download-bytes', 'download-bytes-total',
                     'download-speed', 'download-eta']:
            bind_property(model, name, func_a_to_b=self._update_download_msg)
        bind_property(model, 'download-progress',
                      func_a_to_b=self._update_download_progress)
        model.connect('download-pulse', self._update_download_progress)
        for name in ['download-playlist-count', 'download-playlist-index']:
            bind_property(model, name,
                          func_a_to_b=self._update_download_page_title)
        bind_property(model, 'download-title', self.download_title_wdg,
                      'label', func_a_to_b=lambda title: title or '…')
        bind_property(model, 'download-thumbnail',
                      func_a_to_b=self._add_thumbnail)
        bind_property(self.download_images_wdg, 'transition-running',
                      func_a_to_b=lambda b: b or self._clean_thumbnails())

        def bind_color_wdg(color_wdg, color_scheme):
            bind_property(application, 'color-scheme', color_wdg, 'active',
                          lambda cs: cs == color_scheme or None,
                          lambda b: color_scheme if b else None, bi=True)
        for args in [(self.color_system_wdg, 'system'),
                     (self.color_light_wdg, 'light'),
                     (self.color_dark_wdg, 'dark')]:
            bind_color_wdg(*args)

    def _update_download_progress(self, *_):
        progress = self.model.download_progress
        if progress < 0:
            self.download_progress_wdg.pulse()
        else:
            self.download_progress_wdg.set_fraction(progress)

    def _update_download_page_title(self, _):
        playlist_count = self.model.download_playlist_count
        playlist_index = self.model.download_playlist_index
        s = N_('Downloading')
        if playlist_count > 1:
            s += ' (' + N_('{} of {}').format(
                playlist_index + 1, playlist_count) + ')'
        self.download_page_title_wdg.set_text(s)

    def _update_download_msg(self, _):
        def filesize_fmt(num, suffix='B'):
            for unit in ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
                if abs(num) < 1000:
                    break
                num /= 1000
            return locale.format_string('%.1f %s%s', (num, unit, suffix))

        bytes_ = self.model.download_bytes
        bytes_total = self.model.download_bytes_total
        speed = self.model.download_speed
        eta = self.model.download_eta
        eta_h = eta // 60 // 60
        eta_m = eta // 60 % 60
        eta_s = eta % 60
        msg = '%d∶%02d∶%02d' % (eta_h, eta_m, eta_s) if eta >= 0 else ''
        if msg and (speed >= 0 or bytes_ >= 0 or bytes_total >= 0):
            msg += ' - '
        if bytes_ >= 0 or bytes_total >= 0:
            msg += N_('{} of {}').format(
                filesize_fmt(bytes_) if bytes_ >= 0 else N_('unknown'),
                filesize_fmt(bytes_total) if bytes_total >= 0
                else N_('unknown'))
            if speed >= 0:
                msg += ' (' + filesize_fmt(speed, 'B/s') + ')'
        elif speed >= 0:
            msg += filesize_fmt(speed, 'B/s')
        self.download_info_wdg.set_text(msg)

    def _add_thumbnail(self, thumbnail):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                thumbnail, math.ceil(DOWNLOAD_IMAGE_SIZE * MAX_ASPECT_RATIO),
                DOWNLOAD_IMAGE_SIZE)
        except GLib.Error:
            img_wdg = Gtk.Image.new_from_icon_name(
                'video-x-generic', Gtk.IconSize.INVALID)
            img_wdg.set_pixel_size(DOWNLOAD_IMAGE_SIZE)
        else:
            img_wdg = Gtk.Image.new_from_pixbuf(pixbuf)
        img_wdg.show()
        self.download_images_wdg.add(img_wdg)
        self.download_images_wdg.set_visible_child(img_wdg)

    def _clean_thumbnails(self):
        visible_child_wdg = self.download_images_wdg.get_visible_child()
        for child_wdg in self.download_images_wdg.get_children():
            if child_wdg is not visible_child_wdg:
                self.download_images_wdg.remove(child_wdg)

    def _update_open_download_dir_wdg_tooltip(self, download_dir_abs):
        tooltip_dir = download_dir_abs
        home_dir = os.path.expanduser('~')
        if os.path.commonpath([home_dir, tooltip_dir]) == home_dir:
            tooltip_dir = '~' + tooltip_dir[len(home_dir):]
        self.open_download_dir_wdg.set_tooltip_text(tooltip_dir)

    def _update_focus_and_default(self, _):
        state = self.main_stack_wdg.get_visible_child_name()
        mode = self.audio_video_stack_wdg.get_visible_child_name()
        if state == 'start':
            if mode == 'audio':
                self.audio_download_wdg.grab_default()
                self.audio_url_wdg.grab_focus()
            elif mode == 'video':
                self.video_download_wdg.grab_default()
                self.video_url_wdg.grab_focus()
            else:
                assert False, 'unreachable'
        elif state in ['download', 'cancel']:
            self.download_cancel_wdg.grab_focus()
        elif state == 'error':
            self.error_back_wdg.grab_focus()
        elif state == 'success':
            self.open_download_dir_wdg.grab_focus()
        else:
            assert False, 'unreachable'

    def _hide_notification(self):
        self.get_application().withdraw_notification(self.uuid)

    def _update_notification(self, state):
        self._hide_notification()
        if state not in ('error', 'success') or self.is_active():
            return
        notification = Gio.Notification()
        if state == 'error':
            notification.set_title(N_('Download failed'))
            action_name_with_uuid = 'app.notification-error--%s' % self.uuid
            notification.set_default_action(action_name_with_uuid)
        elif state == 'success':
            notification.set_title(N_('Download finished'))
            action_name_with_uuid = 'app.notification-success--%s' % self.uuid
            notification.set_default_action(action_name_with_uuid)
            button_action_name_with_uuid = (
                'app.notification-open-download-dir--%s' % self.uuid)
            notification.add_button(N_('Open Download Location'),
                                    button_action_name_with_uuid)
        else:
            assert False, 'unreachable'
        self.get_application().send_notification(self.uuid, notification)

    def on_notification_action(self, action_name):
        if action_name in ('notification-success', 'notification-error'):
            self.present()
        elif (action_name == 'notification-open-download-dir' and
                self.model.state == 'success'):
            self.model.open_download_dir()
        else:
            g_log(None, GLib.LogLevelFlags.LEVEL_WARNING,
                  'Action %r not supported in state %r',
                  action_name, self.model.state)

    def _show_about_dialog(self):
        dialog = AboutDialog(self, self.get_application().version)
        dialog.run()
        dialog.destroy()

    def on_playlist_request(self):
        dialog = PlaylistDialog(self)
        res = dialog.run()
        dialog.destroy()
        return res == Gtk.ResponseType.YES

    def on_login_request(self):
        dialog = LoginDialog(self)
        res = dialog.run()
        dialog.destroy()
        if res == Gtk.ResponseType.OK:
            return (dialog.username, dialog.password)
        self.lookup_action('cancel').activate()
        return ('', '')

    def on_videopassword_request(self):
        dialog = PasswordDialog(self)
        res = dialog.run()
        dialog.destroy()
        if res == Gtk.ResponseType.OK:
            return dialog.password
        self.lookup_action('cancel').activate()
        return ''

    def do_destroy(self):
        self.model.shutdown()
        self._hide_notification()
        Handy.ApplicationWindow.do_destroy(self)
