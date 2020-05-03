# authentication_dialog.py
#
# Copyright 2019 Unrud <unrud@outlook.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gettext

from gi.repository import Gtk, GObject

from video_downloader.util import bind_property

N_ = gettext.gettext


class BaseAuthenticationDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(
            N_('Authentication Required'), parent,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            use_header_bar=True)
        self.set_resizable(False)
        self.add_button(N_('Cancel'), Gtk.ResponseType.CANCEL)
        self._ok_button = self.add_button('', Gtk.ResponseType.OK)
        self._update_response(False)
        self.set_default_response(Gtk.ResponseType.OK)
        area_wdg = self.get_content_area()
        area_wdg.add(self._build_content())

    def _update_response(self, form_filled):
        self._ok_button.set_label(N_('Sign in') if form_filled else N_('Skip'))

    def _build_content(self):
        raise NotImplementedError


class LoginDialog(BaseAuthenticationDialog):
    username = GObject.Property(type=str)
    password = GObject.Property(type=str)

    def _update_form(self, _):
        self._update_response(self.username or self.password)

    def _build_content(self):
        content = LoginDialogContent()
        bind_property(self, 'username', content.username_wdg, 'text', bi=True)
        bind_property(self, 'password', content.password_wdg, 'text', bi=True)
        for prop in ['username', 'password']:
            bind_property(self, prop, func_a_to_b=self._update_form)
            bind_property(self, prop, func_a_to_b=self._update_form)
        return content


class PasswordDialog(BaseAuthenticationDialog):
    password = GObject.Property(type=str)

    def _update_form(self, _):
        self._update_response(self.password)

    def _build_content(self):
        content = PasswordDialogContent()
        bind_property(self, 'password', content.password_wdg, 'text', bi=True)
        bind_property(self, 'password', func_a_to_b=self._update_form)
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
