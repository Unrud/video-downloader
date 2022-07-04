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
import os
import sys

from gi.repository import Gdk, Gio, GLib, Gtk, GObject, Handy

from video_downloader.util import bind_property
from video_downloader.window import NOTIFICATION_ACTIONS, Window

N_ = gettext.gettext


class Application(Gtk.Application):
    color_scheme = GObject.Property(type=str)

    def __init__(self, version):
        super().__init__(application_id='com.github.unrud.VideoDownloader')
        self.add_main_option(
            'url', ord('u'), GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
            N_('Prefill URL field'), 'URL')
        GLib.set_application_name(N_('Video Downloader'))
        self.version = version
        self._active_windows = {}

    @staticmethod
    def _subtitle_languages_from_locale():
        languages = []
        for envar in ['LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG']:
            val = os.environ.get(envar)
            if val:
                languages = val.split(':')
                break
        if 'C' not in languages:
            languages.append('C')
        subtitle_languages = []
        for lang in languages:
            lang = locale.normalize(lang)
            for sep in ['@', '.', '_']:
                lang = lang.split(sep, maxsplit=1)[0]
            if lang == 'C':
                lang = 'en'
            if lang not in subtitle_languages:
                subtitle_languages.append(lang)
        return subtitle_languages

    def _on_color_scheme_changed(self, value):
        style_manager = Handy.StyleManager.get_default()
        if value == 'system':
            style_manager.set_color_scheme(Handy.ColorScheme.PREFER_LIGHT)
        elif value == 'light':
            style_manager.set_color_scheme(Handy.ColorScheme.FORCE_LIGHT)
        elif value == 'dark':
            style_manager.set_color_scheme(Handy.ColorScheme.FORCE_DARK)
        else:
            assert False, ('invalid value for \'color-scheme\' property: %r' %
                           value)
    
    def _open_response_cb(self, dialog, response_id):
        open_dialog = dialog

        # Case the user has confirmed the directory.
        if response_id == Gtk.ResponseType.OK:
            folder_path = open_dialog.get_current_folder()
            # Sanity check.
            if folder_path:
                self.settings.set_string("download-folder", folder_path)
                # Updates the current folder to all windows.
                for win in self._active_windows:
                    self._active_windows[win].model.download_dir = self.settings.get_string('download-folder')
        
        dialog.destroy()
    
    def _change_output(self, action):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )

        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK)

        dialog.set_modal(True)
        dialog.connect("response", self._open_response_cb)
        dialog.show()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Handy.init()
        self.settings = Gio.Settings.new(self.props.application_id)
        self.settings.bind('color-scheme', self, 'color-scheme',
                           Gio.SettingsBindFlags.DEFAULT)
        bind_property(self, 'color-scheme',
                      func_a_to_b=self._on_color_scheme_changed)
        # Setup actions
        new_window_action = Gio.SimpleAction.new(
            'new-window', GLib.VariantType('s'))
        new_window_action.connect(
            'activate', lambda _, param: self._new_window(param.get_string()))
        self.add_action(new_window_action)

        output_action = Gio.SimpleAction.new(
            'change-output', GLib.VariantType('s'))
        output_action.connect(
            'activate', lambda _, param: self._change_output(param.get_string())
        )
        self.add_action(output_action)
        
        # Setup CSS
        css_uri = 'resource:///com/github/unrud/VideoDownloader/style.css'
        css_provider = Gtk.CssProvider()
        css_provider.load_from_file(Gio.File.new_for_uri(css_uri))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def _new_window(self, url=''):
        win = Window(self)
        win.set_default_icon_name(self.props.application_id)
        model = win.model
        model.url = url
        # Apply/Bind settings
        model.download_dir = self.settings.get_string('download-folder')
        model.prefer_mpeg = self.settings.get_boolean('prefer-mpeg')
        model.automatic_subtitles = [
            *self._subtitle_languages_from_locale(),
            *self.settings.get_strv('automatic-subtitles')]
        self.settings.bind('mode', model, 'mode', (
                               Gio.SettingsBindFlags.DEFAULT |
                               Gio.SettingsBindFlags.GET_NO_CHANGES))
        r = self.settings.get_uint('resolution')
        for resolution in sorted(x[0] for x in model.resolutions):
            if r <= resolution:
                break
        model.resolution = resolution
        self.settings.bind('resolution', model, 'resolution',
                           Gio.SettingsBindFlags.SET)
        # Add to window list
        self._active_windows[win.uuid] = win
        # Register window notification actions
        for action_name in NOTIFICATION_ACTIONS:
            action_name_with_uuid = '%s--%s' % (action_name, win.uuid)
            action = Gio.SimpleAction.new(action_name_with_uuid)
            action.connect('activate', self._dispatch_notification_action)
            self.add_action(action)
        win.connect('destroy', self._on_destroy_window)
        win.present()

    def _on_destroy_window(self, win):
        for action_name in NOTIFICATION_ACTIONS:
            action_name_with_uuid = '%s--%s' % (action_name, win.uuid)
            self.remove_action(action_name_with_uuid)
        del self._active_windows[win.uuid]

    def _dispatch_notification_action(self, action, param):
        action_name_with_uuid = action.get_name()
        for action_name in NOTIFICATION_ACTIONS:
            prefix = '%s--' % action_name
            if action_name_with_uuid.startswith(prefix):
                uuid = action_name_with_uuid[len(prefix):]
                break
        else:
            assert False, 'unreachable'
        try:
            win = self._active_windows[uuid]
        except KeyError:
            return
        win.on_notification_action(action_name)

    def do_activate(self):
        self._new_window()

    def do_handle_local_options(self, options):
        url_variant = options.lookup_value('url', GLib.VariantType('s'))
        if url_variant:
            self.register()
            self.activate_action('new-window', url_variant)
            return 0
        return -1


def main(version):
    app = Application(version)
    return app.run(sys.argv)
