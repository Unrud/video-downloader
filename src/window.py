# Copyright (C) 2019 Unrud <unrud@outlook.com>
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

from gi.repository import GLib, Gtk, GdkPixbuf, GObject, Handy

from video_downloader.util import bind_property

DOWNLOAD_IMAGE_SIZE = 128
MAX_ASPECT_RATIO = 2.39
N_ = gettext.gettext


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/window.ui')
class Window(Handy.ApplicationWindow):
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
    success_msg_wdg = Gtk.Template.Child()
    download_title_wdg = Gtk.Template.Child()
    download_progress_wdg = Gtk.Template.Child()
    download_info_wdg = Gtk.Template.Child()
    download_images_wdg = Gtk.Template.Child()
    error_details_expander_wdg = Gtk.Template.Child()
    error_details_revealer_wdg = Gtk.Template.Child()
    light_mode_wdg = Gtk.Template.Child()
    dark_mode_wdg = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = self.get_application().model
        bind_property(self.model, 'error', self.error_buffer, 'text')
        bind_property(self.error_details_expander_wdg, 'expanded',
                      self.error_details_revealer_wdg, 'reveal-child')
        bind_property(self.model, 'url', self.audio_url_wdg, 'text', bi=True)
        bind_property(self.model, 'url', self.video_url_wdg, 'text', bi=True)
        for resolution, description in self.model.resolutions:
            it = self.resolutions_store.append()
            self.resolutions_store.set(it, 0, str(resolution), 1, description)
        bind_property(self.model, 'resolution', self.resolution_wdg,
                      'active-id', str, int, bi=True)
        bind_property(
            self.model, 'state', self.main_stack_wdg, 'visible-child-name',
            lambda s: {'cancel': 'download'}.get(s, s))
        bind_property(self.model, 'mode', self.audio_video_stack_wdg,
                      'visible-child-name', bi=True)
        bind_property(self.main_stack_wdg, 'visible-child-name',
                      func_a_to_b=self._update_focus_and_default)
        bind_property(self.audio_video_stack_wdg, 'visible-child-name',
                      func_a_to_b=self._update_focus_and_default)
        bind_property(self.model, 'download-dir-abs',
                      func_a_to_b=self._update_success_msg)
        self.success_msg_wdg.connect('activate-link', self._on_activate_link)
        for name in ['download-bytes', 'download-bytes-total',
                     'download-speed', 'download-eta']:
            bind_property(
                self.model, name, func_a_to_b=self._update_download_msg)
        bind_property(self.model, 'download-progress',
                      func_a_to_b=self._update_download_progress)
        self.model.connect('download-pulse', self._update_download_progress)
        for name in ['download-title', 'download-playlist-count',
                     'download-playlist-index']:
            bind_property(
                self.model, name, func_a_to_b=self._update_download_title)
        bind_property(self.model, 'download-thumbnail',
                      func_a_to_b=self._add_thumbnail)
        bind_property(self.download_images_wdg, 'transition-running',
                      func_a_to_b=lambda b: b or self._clean_thumbnails())

        bind_property(self.model, 'darkmode',
                      self.dark_mode_wdg, 'active',
                      bi=True)

        bind_property(self.model, 'darkmode', func_a_to_b=lambda x: Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme', x))

    def _update_download_progress(self, *_):
        progress = self.model.download_progress
        if progress < 0:
            self.download_progress_wdg.pulse()
        else:
            self.download_progress_wdg.set_fraction(progress)

    def _update_download_title(self, _):
        title = self.model.download_title
        playlist_count = self.model.download_playlist_count
        playlist_index = self.model.download_playlist_index
        s = N_('Downloading')
        if playlist_count > 1:
            s += ' (' + N_('{} of {}').format(
                playlist_index + 1, playlist_count) + ')'
        if title:
            s += ': ' + title
        self.download_title_wdg.set_text(s)

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

    def _update_success_msg(self, download_dir_abs):
        label_dir = download_dir_abs
        home_dir = os.path.expanduser('~')
        if os.path.commonpath([home_dir, label_dir]) == home_dir:
            label_dir = '~' + label_dir[len(home_dir):]
        template = GObject.markup_escape_text(N_('Saved in {}'))
        link = '<a href="action:open-download-dir">{}</a>'.format(
            GObject.markup_escape_text(label_dir))
        self.success_msg_wdg.set_markup(template.format(link))

    def _on_activate_link(self, _, uri):
        if uri.startswith('action:'):
            action = self.get_application().lookup_action(uri[len('action:'):])
            action.activate()
            return True
        return False

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
                assert False
        elif state in ['download', 'cancel']:
            self.download_cancel_wdg.grab_focus()
        elif state == 'error':
            self.error_back_wdg.grab_focus()
        elif state == 'success':
            self.success_back_wdg.grab_focus()
        else:
            assert False

