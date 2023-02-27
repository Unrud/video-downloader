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

from gi.repository import GObject, Gtk

from video_downloader.util.connection import CloseStack, PropertyBinding

N_ = gettext.gettext


class BaseAuthenticationDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(modal=True, destroy_with_parent=True, resizable=False,
                         title=N_('Authentication Required'),
                         use_header_bar=True)
        self._cs = CloseStack()
        self.set_transient_for(parent)
        self.add_button(N_('Cancel'), Gtk.ResponseType.CANCEL)
        self._ok_button = self.add_button('', Gtk.ResponseType.OK)
        self._update_response(False)
        self.set_default_response(Gtk.ResponseType.OK)
        area_wdg = self.get_content_area()
        area_wdg.append(self._build_content())

    def destroy(self):
        self._cs.close()
        super().destroy()

    def _update_response(self, form_filled):
        self._ok_button.set_label(N_('Sign in') if form_filled else N_('Skip'))

    def _build_content(self):
        raise NotImplementedError


class LoginDialog(BaseAuthenticationDialog):
    username = GObject.Property(type=str)
    password = GObject.Property(type=str)

    def _update_form(self):
        self._update_response(self.username or self.password)

    def _build_content(self):
        content = LoginDialogContent()
        self._cs.push(PropertyBinding(
            self, 'username', content.username_wdg, 'text', bi=True))
        self._cs.push(PropertyBinding(
            self, 'password', content.password_wdg, 'text', bi=True))
        self._cs.push(PropertyBinding(
            self, 'username', func_a_to_b=lambda _: self._update_form()))
        self._cs.push(PropertyBinding(
            self, 'password', func_a_to_b=lambda _: self._update_form()))
        return content


class PasswordDialog(BaseAuthenticationDialog):
    password = GObject.Property(type=str)

    def _update_form(self):
        self._update_response(self.password)

    def _build_content(self):
        content = PasswordDialogContent()
        self._cs.push(PropertyBinding(
            self, 'password', content.password_wdg, 'text', bi=True))
        self._cs.push(PropertyBinding(
            self, 'password', func_a_to_b=lambda _: self._update_form()))
        return content


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/'
                            'authentication_dialog_login.ui')
class LoginDialogContent(Gtk.Box):
    __gtype_name__ = 'VideoDownloaderLoginDialogContent'
    username_wdg = Gtk.Template.Child()
    password_wdg = Gtk.Template.Child()


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/'
                            'authentication_dialog_password.ui')
class PasswordDialogContent(Gtk.Box):
    __gtype_name__ = 'VideoDownloaderPasswordDialogContent'
    password_wdg = Gtk.Template.Child()
