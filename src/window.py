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

import functools
import gettext
import locale
import math
import os
import uuid

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

from video_downloader.about_dialog import build_about_dialog
from video_downloader.authentication_dialog import LoginDialog, PasswordDialog
from video_downloader.model import HandlerInterface, Model, check_download_dir
from video_downloader.playlist_dialog import PlaylistDialog
from video_downloader.shortcuts_dialog import ShortcutsDialog
from video_downloader.util import gobject_log
from video_downloader.util.connection import (CloseStack, PropertyBinding,
                                              SignalConnection, create_action)
from video_downloader.util.path import expand_path, open_in_file_manager
from video_downloader.util.response import AsyncResponse

DOWNLOAD_IMAGE_SIZE = 128
MAX_ASPECT_RATIO = 2.39
N_ = gettext.gettext


class SuccessDetailsController:
    def __init__(self, text_view):
        self._cs = CloseStack()
        self._text_view = text_view
        self._text_buffer = gobject_log(Gtk.TextBuffer.new())
        self._text_buffer.set_enable_undo(False)
        self._text_view.set_buffer(self._text_buffer)
        self._hovering_over_link = None

        controller_key = gobject_log(Gtk.EventControllerKey.new())
        self._cs.push(SignalConnection(
            controller_key, 'key-pressed', self._key_pressed))
        self._text_view.add_controller(controller_key)
        controller_motion = gobject_log(Gtk.EventControllerMotion.new())
        self._cs.push(SignalConnection(
            controller_motion, 'motion', self._motion_callback))
        self._text_view.add_controller(controller_motion)
        controller_click = gobject_log(Gtk.GestureClick.new())
        self._cs.push(SignalConnection(
            controller_click, 'released', self._released_callback))
        self._text_view.add_controller(controller_click)

    def clear(self):
        self._text_buffer.set_text('')
        tag_table = self._text_buffer.get_tag_table()
        tags = []
        tag_table.foreach(tags.append)
        for tag in tags:
            tag_table.remove(tag)

    def add_link(self, text, callback, *callback_args):
        tag = gobject_log(self._text_buffer.create_tag(
            foreground='blue', underline=Pango.Underline.SINGLE))
        tag.link_callback = functools.partial(callback, *callback_args)
        iter_ = self._text_buffer.get_end_iter()
        if not iter_.is_start():
            self._text_buffer.insert(iter_, "\n")
        self._text_buffer.insert_with_tags(iter_, text, tag)

    def shutdown(self):
        self._cs.close()

    def _key_pressed(self, controller, keyval, keycode, modifiers):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            iter_ = self._text_buffer.get_iter_at_mark(
                self._text_buffer.get_insert())
            for tag in iter_.get_tags():
                if hasattr(tag, 'link_callback'):
                    tag.link_callback()
        return Gdk.EVENT_PROPAGATE

    def _motion_callback(self, controller, x, y):
        tx, ty = self._text_view.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, x, y)
        over_text, iter_ = self._text_view.get_iter_at_location(tx, ty)
        hovering = False
        if over_text:
            for tag in iter_.get_tags():
                if hasattr(tag, 'link_callback'):
                    hovering = True
                    break
        if self._hovering_over_link != hovering:
            self._text_view.set_cursor_from_name(
                'pointer' if hovering else 'text')
            self._hovering_over_link = hovering

    def _released_callback(self, gesture, n_press, x, y):
        if gesture.get_button() > 1:
            return
        tx, ty = self._text_view.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, x, y)
        over_text, iter_ = self._text_view.get_iter_at_location(tx, ty)
        if not over_text:
            return
        for tag in iter_.get_tags():
            if hasattr(tag, 'link_callback'):
                tag.link_callback()


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/window.ui')
class Window(Adw.ApplicationWindow, HandlerInterface):
    __gtype_name__ = 'VideoDownloaderWindow'
    error_buffer = Gtk.Template.Child()
    success_details_view_wdg = Gtk.Template.Child()
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
        create_action(self, self._cs, 'close', self.destroy, no_args=True)
        create_action(self, self._cs, 'about', self._show_about_dialog,
                      no_args=True)
        create_action(self, self._cs, 'shortcuts', self._show_shortcuts_dialog,
                      no_args=True)
        create_action(self, self._cs, 'change-download-folder',
                      self._change_download_folder, no_args=True)
        create_action(
            self, self._cs, 'set-audio-video-page',
            lambda _, param: self.audio_video_stack_wdg.set_visible_child_name(
                                 param.get_string()),
            parameter_type=GLib.VariantType('s'))
        # Register notifcation actions
        self._notification_uuid = str(uuid.uuid4())
        create_action(application, self._cs, 'notification-success--' +
                      self._notification_uuid, self.present, no_args=True)
        create_action(application, self._cs, 'notification-error--' +
                      self._notification_uuid, self.present, no_args=True)
        create_action(
            application, self._cs, 'notification-open-finished-download-dir--'
            + self._notification_uuid, self.model.actions.activate_action,
            'open-finished-download-dir', no_args=True)
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
            self.model, 'prefer-mpeg', self.prefer_mpeg_wdg, 'active',
            bi=True))
        self._cs.push(PropertyBinding(
            self.model, 'state', self.main_stack_wdg, 'visible-child-name',
            func_a_to_b=lambda s: {'prepare': 'download',
                                   'cancel': 'download'}.get(s, s)))
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
        self._success_details_controller = SuccessDetailsController(
            self.success_details_view_wdg)
        self._cs.add_close_callback(self._success_details_controller.shutdown)
        self._cs.push(PropertyBinding(
            self.model, 'finished-download-filenames',
            func_a_to_b=self._update_success_details))
        # Workaround for focusing AdwEntryRow at program startup
        self._cs.push(SignalConnection(
            self, 'show', self._update_focus_and_default, no_args=True))

    def _update_success_details(self, filenames):
        self._success_details_controller.clear()
        for filename in filenames or []:
            self._success_details_controller.add_link(
                filename, open_in_file_manager,
                self.model.finished_download_dir, [filename])

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
                'app.notification-error--' + self._notification_uuid)
        elif state == 'success':
            notification.set_title(N_('Download finished'))
            notification.set_default_action(
                'app.notification-success--' + self._notification_uuid)
            notification.add_button(
                N_('Open Download Location'),
                'app.notification-open-finished-download-dir--' +
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

    def on_download_folder_error(self, title, message, path,
                                 show_reset_button=True):
        def handle_response(dialog, res):
            if res == RESPONSE_TYPE_CHANGE:
                self._change_download_folder().chain(async_response)
                connection.close()
            elif res == RESPONSE_TYPE_RESET:
                self.application.settings.reset('download-folder')
                async_response.set_result(None)
            else:
                async_response.cancel()
        RESPONSE_TYPE_RESET = 100
        RESPONSE_TYPE_CHANGE = 101
        if path is not None:
            message = '%s: %r' % (message, path) if message else repr(path)
        dialog = Gtk.MessageDialog(
            modal=True, destroy_with_parent=True,
            message_type=Gtk.MessageType.ERROR, text=title,
            secondary_text=message, buttons=Gtk.ButtonsType.CANCEL)
        if show_reset_button:
            dialog.add_button(N_('Reset to Default'), RESPONSE_TYPE_RESET)
        dialog.add_button(N_('Change Download Location'), RESPONSE_TYPE_CHANGE)
        dialog.set_default_response(RESPONSE_TYPE_CHANGE)
        dialog.set_transient_for(self)
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        async_response = AsyncResponse()
        async_response.add_close_callback(connection.close)
        self._cs.push(async_response)
        dialog.show()
        return async_response

    def _change_download_folder(self):
        def handle_callback(dialog, task):
            try:
                file = dialog.select_folder_finish(task)
            except GLib.GError:
                # Dialog cancelled
                async_response.cancel()
                return
            message = path = None
            if file and file.get_path():
                path = file.get_path()
                message = check_download_dir(expand_path(path))
                if message is None:
                    self.model.download_folder = path
                    async_response.set_result(None)
                    return
            else:
                message = N_('Not a directory')
            self.on_download_folder_error(
                N_('Invalid folder selected'), message, path,
                show_reset_button=False).chain(async_response)
        dialog = gobject_log(Gtk.FileDialog(
            modal=True, title=N_('Change Download Location'),
            accept_label=N_('Select Folder')))
        cancellable = Gio.Cancellable()
        async_response = AsyncResponse()
        async_response.add_close_callback(cancellable.cancel)
        self._cs.push(async_response)
        dialog.select_folder(self, cancellable, handle_callback)
        return async_response

    def on_playlist_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.NO:
                async_response.set_result(False)
            elif res == Gtk.ResponseType.YES:
                async_response.set_result(True)
            else:
                async_response.cancel()
        dialog = gobject_log(PlaylistDialog(self))
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        async_response = AsyncResponse()
        async_response.add_close_callback(connection.close)
        self._cs.push(async_response)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def on_login_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.OK:
                async_response.set_result((dialog.username, dialog.password))
            else:
                async_response.cancel()
        dialog = gobject_log(LoginDialog(self))
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        async_response = AsyncResponse()
        async_response.add_close_callback(connection.close)
        self._cs.push(async_response)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def on_password_request(self):
        def handle_response(dialog, res):
            if res == Gtk.ResponseType.OK:
                async_response.set_result(dialog.password)
            else:
                async_response.cancel()
        dialog = gobject_log(PasswordDialog(self))
        connection = SignalConnection(dialog, 'response', handle_response)
        connection.add_close_callback(dialog.destroy)
        async_response = AsyncResponse()
        async_response.add_close_callback(connection.close)
        self._cs.push(async_response)
        self.window_group.add_window(dialog)
        dialog.show()
        return async_response

    def destroy(self):
        self._hide_notification()
        self._cs.close()
        super().destroy()
