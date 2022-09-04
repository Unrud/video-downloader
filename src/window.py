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

from gi.repository import Adw, GdkPixbuf, Gio, GLib, Gtk

from video_downloader.about_dialog import AboutDialog
from video_downloader.authentication_dialog import LoginDialog, PasswordDialog
from video_downloader.model import Handler, Model
from video_downloader.playlist_dialog import PlaylistDialog
from video_downloader.util import ConnectionManager, gobject_log

DOWNLOAD_IMAGE_SIZE = 128
MAX_ASPECT_RATIO = 2.39
N_ = gettext.gettext


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/window.ui')
class Window(Adw.ApplicationWindow, Handler):
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
    finished_download_dir_wdg = Gtk.Template.Child()
    download_page_title_wdg = Gtk.Template.Child()
    download_title_wdg = Gtk.Template.Child()
    download_progress_wdg = Gtk.Template.Child()
    download_info_wdg = Gtk.Template.Child()
    download_images_wdg = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)
        gobject_log(self)
        self._cm = ConnectionManager()
        self.application = application
        self.model = model = Model(self)
        self.window_group = gobject_log(Gtk.WindowGroup())
        self.window_group.add_window(self)
        # Setup actions
        for action_name in model.actions.list_actions():
            self.add_action(model.actions.lookup_action(action_name))
        about_action = gobject_log(Gio.SimpleAction.new('about', None),
                                   'about')
        self._cm.connect(about_action, 'activate', self._show_about_dialog,
                         no_args=True)
        self.add_action(about_action)
        # Register notifcation actions
        self._notification_uuid = str(uuid.uuid4())
        for name, callback, *extra_args in [
                ('notification-success', self.present),
                ('notification-error', self.present),
                ('notification-open-finished-download-dir',
                 self.model.actions.activate_action,
                 'open-finished-download-dir')]:
            action = gobject_log(Gio.SimpleAction.new(
                '%s--%s' % (name, self._notification_uuid)), name)
            self._cm.connect(action, 'activate', callback, *extra_args,
                             no_args=True)
            application.add_action(action)
        # Bind properties to UI
        self._cm.bind(model, 'error', self.error_buffer, 'text')
        self._cm.bind(model, 'url', self.audio_url_wdg, 'text', bi=True)
        self._cm.bind(model, 'url', self.video_url_wdg, 'text', bi=True)
        for resolution, description in model.resolutions.items():
            it = self.resolutions_store.append()
            self.resolutions_store.set(it, 0, str(resolution), 1, description)
        self._cm.bind(model, 'resolution', self.resolution_wdg, 'active-id',
                      str, int, bi=True)
        self._cm.bind(
            model, 'state', self.main_stack_wdg, 'visible-child-name',
            func_a_to_b=lambda s: {'cancel': 'download'}.get(s, s))
        self._cm.bind(model, 'state', func_a_to_b=self._update_notification)
        self._cm.bind(model, 'mode', self.audio_video_stack_wdg,
                      'visible-child-name', bi=True)
        self._cm.bind(self.main_stack_wdg, 'visible-child-name',
                      func_a_to_b=self._update_focus_and_default)
        self._cm.bind(self.audio_video_stack_wdg, 'visible-child-name',
                      func_a_to_b=self._update_focus_and_default)
        self._cm.bind(model, 'finished-download-dir', func_a_to_b=(
                          self._update_finished_download_dir_wdg_tooltip))
        for name in ['download-bytes', 'download-bytes-total',
                     'download-speed', 'download-eta']:
            self._cm.bind(model, name, func_a_to_b=self._update_download_msg)
        self._cm.bind(model, 'download-progress',
                      func_a_to_b=self._update_download_progress)
        self._cm.connect(model, 'download-pulse',
                         self._update_download_progress, no_args=True)
        for name in ['download-playlist-count', 'download-playlist-index']:
            self._cm.bind(model, name,
                          func_a_to_b=self._update_download_page_title)
        self._cm.bind(model, 'download-title', self.download_title_wdg,
                      'label', func_a_to_b=lambda title: title or '…')
        self._cm.bind(model, 'download-thumbnail',
                      func_a_to_b=self._add_thumbnail)
        self._cm.bind(self.download_images_wdg, 'transition-running',
                      func_a_to_b=lambda b: b or self._clean_thumbnails())

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
            pixbuf = gobject_log(GdkPixbuf.Pixbuf.new_from_file_at_size(
                thumbnail, math.ceil(DOWNLOAD_IMAGE_SIZE * MAX_ASPECT_RATIO),
                DOWNLOAD_IMAGE_SIZE))
        except GLib.Error:
            img_wdg = gobject_log(Gtk.Image.new_from_icon_name(
                'video-x-generic'))
            img_wdg.set_pixel_size(DOWNLOAD_IMAGE_SIZE)
        else:
            img_wdg = gobject_log(Gtk.Picture.new_for_pixbuf(pixbuf))
        img_wdg.set_size_request(-1, DOWNLOAD_IMAGE_SIZE)
        self.download_images_wdg.add_child(img_wdg)
        self.download_images_wdg.set_visible_child(img_wdg)

    def _clean_thumbnails(self):
        visible_child_wdg = self.download_images_wdg.get_visible_child()
        for page in list(self.download_images_wdg.get_pages()):
            child_wdg = page.get_child()
            if child_wdg is not visible_child_wdg:
                self.download_images_wdg.remove(child_wdg)

    def _update_finished_download_dir_wdg_tooltip(self, download_dir):
        if download_dir:
            home_dir = os.path.expanduser('~')
            if os.path.commonpath([home_dir, download_dir]) == home_dir:
                download_dir = '~' + download_dir[len(home_dir):]
        self.finished_download_dir_wdg.set_tooltip_text(download_dir)

    def _update_focus_and_default(self, _):
        state = self.main_stack_wdg.get_visible_child_name()
        mode = self.audio_video_stack_wdg.get_visible_child_name()
        if state == 'start':
            if mode == 'audio':
                self.set_default_widget(self.audio_download_wdg)
                self.audio_url_wdg.grab_focus()
            elif mode == 'video':
                self.set_default_widget(self.video_download_wdg)
                self.video_url_wdg.grab_focus()
            else:
                assert False, 'unreachable'
        elif state in ['download', 'cancel']:
            self.download_cancel_wdg.grab_focus()
        elif state == 'error':
            self.error_back_wdg.grab_focus()
        elif state == 'success':
            self.finished_download_dir_wdg.grab_focus()
        else:
            assert False, 'unreachable'

    def _hide_notification(self):
        self.application.withdraw_notification(self._notification_uuid)

    def _update_notification(self, state):
        self._hide_notification()
        if state not in ('error', 'success') or self.is_active():
            return
        notification = gobject_log(Gio.Notification())
        if state == 'error':
            notification.set_title(N_('Download failed'))
            notification.set_default_action(
                'app.notification-error--%s' % self._notification_uuid)
        elif state == 'success':
            notification.set_title(N_('Download finished'))
            notification.set_default_action(
                'app.notification-success--%s' % self._notification_uuid)
            notification.add_button(
                N_('Open Download Location'),
                'app.notification-open-finished-download-dir--%s' %
                self._notification_uuid)
        else:
            assert False, 'unreachable'
        self.application.send_notification(self._notification_uuid,
                                           notification)

    def _show_about_dialog(self):
        dialog = AboutDialog(self, self.application.version)
        self.window_group.add_window(dialog)
        dialog.show()

    def on_playlist_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.NO:
                async_response.respond(False)
            elif res == Gtk.ResponseType.YES:
                async_response.respond(True)
            else:
                self.model.actions.activate_action('cancel')
        dialog = PlaylistDialog(self)
        async_response = Handler.AsyncResponse(dialog.destroy)
        dialog._cm.connect(dialog, 'response', handle_response)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def on_login_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.OK:
                async_response.respond((dialog.username, dialog.password))
            else:
                self.model.actions.activate_action('cancel')
        dialog = LoginDialog(self)
        async_response = Handler.AsyncResponse(dialog.destroy)
        dialog._cm.connect(dialog, 'response', handle_response)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def on_password_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.OK:
                async_response.respond(dialog.password)
            else:
                self.model.actions.activate_action('cancel')
        dialog = PasswordDialog(self)
        async_response = Handler.AsyncResponse(dialog.destroy)
        dialog._cm.connect(dialog, 'response', handle_response)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def destroy(self):
        self._hide_notification()
        for action_name in self.application.list_actions():
            if action_name.endswith('--%s' % self._notification_uuid):
                self.application.remove_action(action_name)
        self._cm.disconnect()
        for action_name in self.list_actions():
            self.remove_action(action_name)
        self.model.shutdown()
        self.model = None
        super().destroy()
