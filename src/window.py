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

from video_downloader.about_dialog import build_about_dialog
from video_downloader.authentication_dialog import LoginDialog, PasswordDialog
from video_downloader.model import HandlerInterface, Model
from video_downloader.playlist_dialog import PlaylistDialog
from video_downloader.shortcuts_dialog import ShortcutsDialog
from video_downloader.util import (CloseStack, PropertyBinding,
                                   SignalConnection, gobject_log)

DOWNLOAD_IMAGE_SIZE = 128
MAX_ASPECT_RATIO = 2.39
N_ = gettext.gettext


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/window.ui')
class Window(Adw.ApplicationWindow, HandlerInterface):
    __gtype_name__ = 'VideoDownloaderWindow'
    error_buffer = Gtk.Template.Child()
    audio_url_wdg = Gtk.Template.Child()
    video_url_wdg = Gtk.Template.Child()
    resolution_wdg = Gtk.Template.Child()
    prefer_mpeg_wdg = Gtk.Template.Child()
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
        self._cs = CloseStack()
        self.application = application
        self.model = gobject_log(Model(self))
        self._cs.add_close_callback(self.model.shutdown)
        self.window_group = gobject_log(Gtk.WindowGroup())
        self.window_group.add_window(self)
        # Setup actions
        for action_name in self.model.actions.list_actions():
            self.add_action(self.model.actions.lookup_action(action_name))
            self._cs.add_close_callback(self.remove_action, action_name)
        for action_name, callback in [
                ('close', self.destroy), ('about', self._show_about_dialog),
                ('shortcuts', self._show_shortcuts_dialog)]:
            action = gobject_log(Gio.SimpleAction.new(action_name, None),
                                 action_name)
            self._cs.push(SignalConnection(
                action, 'activate', callback, no_args=True))
            self.add_action(action)
            self._cs.add_close_callback(self.remove_action, action_name)
        action_name = 'set-audio-video-page'
        action = gobject_log(Gio.SimpleAction.new(
            action_name, GLib.VariantType('s')), action_name)
        self._cs.push(SignalConnection(
            action, 'activate',
            lambda _, param: self.audio_video_stack_wdg.set_visible_child_name(
                                 param.get_string())))
        self.add_action(action)
        self._cs.add_close_callback(self.remove_action, action_name)
        # Register notifcation actions
        self._notification_uuid = str(uuid.uuid4())
        for name, callback, *extra_args in [
                ('notification-success', self.present),
                ('notification-error', self.present),
                ('notification-open-finished-download-dir',
                 self.model.actions.activate_action,
                 'open-finished-download-dir')]:
            action_name = '%s--%s' % (name, self._notification_uuid)
            action = gobject_log(Gio.SimpleAction.new(action_name), name)
            self._cs.push(SignalConnection(
                action, 'activate', callback, *extra_args, no_args=True))
            application.add_action(action)
            self._cs.add_close_callback(application.remove_action, action_name)
        # Bind properties to UI
        self._cs.push(PropertyBinding(
            self.model, 'error', self.error_buffer, 'text'))
        self._cs.push(PropertyBinding(
            self.model, 'url', self.audio_url_wdg, 'text', bi=True))
        self._cs.push(PropertyBinding(
            self.model, 'url', self.video_url_wdg, 'text', bi=True))
        for description in self.model.resolutions.values():
            self.resolution_wdg.get_model().append(description)
        self._cs.push(PropertyBinding(
            self.model, 'resolution', self.resolution_wdg, 'selected',
            lambda r: list(self.model.resolutions).index(r),
            lambda i: list(self.model.resolutions)[i], bi=True))
        self._cs.push(PropertyBinding(
            self.model, 'prefer-mpeg', self.prefer_mpeg_wdg, 'state', bi=True))
        self._cs.push(PropertyBinding(
            self.model, 'state', self.main_stack_wdg, 'visible-child-name',
            func_a_to_b=lambda s: {'cancel': 'download'}.get(s, s)))
        self._cs.push(PropertyBinding(
            self.model, 'state', func_a_to_b=self._update_notification))
        self._cs.push(PropertyBinding(
            self.model, 'mode', self.audio_video_stack_wdg,
            'visible-child-name', bi=True))
        self._cs.push(PropertyBinding(
            self.main_stack_wdg, 'visible-child-name',
            func_a_to_b=lambda _: self._update_focus_and_default()))
        self._cs.push(PropertyBinding(
            self.audio_video_stack_wdg, 'visible-child-name',
            func_a_to_b=lambda _: self._update_focus_and_default()))
        self._cs.push(PropertyBinding(
            self.model, 'finished-download-dir',
            func_a_to_b=self._update_finished_download_dir_wdg_tooltip))
        for name in ['download-bytes', 'download-bytes-total',
                     'download-speed', 'download-eta']:
            self._cs.push(PropertyBinding(
                self.model, name,
                func_a_to_b=lambda _: self._update_download_msg()))
        self._cs.push(PropertyBinding(
            self.model, 'download-progress',
            func_a_to_b=lambda _: self._update_download_progress()))
        self._cs.push(SignalConnection(
            self.model, 'download-pulse', self._update_download_progress,
            no_args=True))
        for name in ['download-playlist-count', 'download-playlist-index']:
            self._cs.push(PropertyBinding(
                self.model, name,
                func_a_to_b=lambda _: self._update_download_page_title()))
        self._cs.push(PropertyBinding(
            self.model, 'download-title', self.download_title_wdg, 'label',
            func_a_to_b=lambda title: title or '…'))
        self._cs.push(PropertyBinding(
            self.model, 'download-thumbnail', func_a_to_b=self._add_thumbnail))
        self._cs.push(PropertyBinding(
            self.download_images_wdg, 'transition-running',
            func_a_to_b=lambda b: b or self._clean_thumbnails()))
        # Workaround for focusing AdwEntryRow at program startup
        self._cs.push(SignalConnection(
            self, 'show', self._update_focus_and_default, no_args=True))

    def _update_download_progress(self):
        progress = self.model.download_progress
        if progress < 0:
            self.download_progress_wdg.pulse()
        else:
            self.download_progress_wdg.set_fraction(progress)

    def _update_download_page_title(self):
        playlist_count = self.model.download_playlist_count
        playlist_index = self.model.download_playlist_index
        s = N_('Downloading')
        if playlist_count > 1:
            s += ' (' + N_('{} of {}').format(
                playlist_index + 1, playlist_count) + ')'
        self.download_page_title_wdg.set_text(s)

    def _update_download_msg(self):
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

    def _update_focus_and_default(self):
        state = self.main_stack_wdg.get_visible_child_name()
        mode = self.audio_video_stack_wdg.get_visible_child_name()
        default_wdg = None
        if state == 'start':
            if mode == 'audio':
                default_wdg = self.audio_download_wdg
                self.audio_url_wdg.grab_focus()
            elif mode == 'video':
                default_wdg = self.video_download_wdg
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
        self.set_default_widget(default_wdg)

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

    def _show_shortcuts_dialog(self):
        dialog = gobject_log(ShortcutsDialog(self))
        self.window_group.add_window(dialog)
        dialog.show()

    def _show_about_dialog(self):
        dialog = gobject_log(build_about_dialog(self))
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
        dialog = gobject_log(PlaylistDialog(self))
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        self._cs.push(connection)
        async_response = HandlerInterface.AsyncResponse(connection.close)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def on_login_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.OK:
                async_response.respond((dialog.username, dialog.password))
            else:
                self.model.actions.activate_action('cancel')
        dialog = gobject_log(LoginDialog(self))
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        self._cs.push(connection)
        async_response = HandlerInterface.AsyncResponse(connection.close)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def on_password_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.OK:
                async_response.respond(dialog.password)
            else:
                self.model.actions.activate_action('cancel')
        dialog = gobject_log(PasswordDialog(self))
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        self._cs.push(connection)
        async_response = HandlerInterface.AsyncResponse(connection.close)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def destroy(self):
        self._hide_notification()
        self._cs.close()
        super().destroy()
