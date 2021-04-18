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
import sys

from gi.repository import Gdk, Gio, GLib, Gtk, Handy

from video_downloader.util import g_log
from video_downloader.window import NOTIFICATION_ACTIONS, Window

N_ = gettext.gettext


class Application(Gtk.Application):
    def __init__(self, version):
        super().__init__(application_id='com.github.unrud.VideoDownloader')
        self.add_main_option(
            'url', ord('u'), GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
            N_('Prefill URL field'), 'URL')
        GLib.set_application_name(N_('Video Downloader'))
        self.version = version
        self._active_windows = {}

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Handy.init()
        self.settings = Gio.Settings.new(self.props.application_id)
        self.settings.bind('dark-mode', Gtk.Settings.get_default(),
                           'gtk-application-prefer-dark-theme',
                           Gio.SettingsBindFlags.DEFAULT)
        # Setup actions
        new_window_action = Gio.SimpleAction.new(
            'new-window', GLib.VariantType('s'))
        new_window_action.connect(
            'activate', lambda _, param: self._new_window(param.get_string()))
        self.add_action(new_window_action)
        for action_name in NOTIFICATION_ACTIONS:
            action = Gio.SimpleAction.new(action_name, GLib.VariantType('s'))
            action.connect('activate', self._dispatch_notification_action)
            self.add_action(action)
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
        win.connect('destroy', lambda win: self._active_windows.pop(win.uuid))

        win.present()

    def _dispatch_notification_action(self, action, param):
        action_name = action.get_name()
        uuid = param.get_string()
        win = self._active_windows.get(uuid)
        if win is None:
            g_log(None, GLib.LogLevelFlags.LEVEL_WARNING,
                  'Ignoring action %r for unknown window %r',
                  action_name, uuid)
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
