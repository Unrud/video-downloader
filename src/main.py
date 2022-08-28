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

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, GObject

from video_downloader.util import bind_property
from video_downloader.window import Window

N_ = gettext.gettext


class Application(Adw.Application):
    color_scheme = GObject.Property(type=str)

    def __init__(self, version):
        super().__init__(application_id='com.github.unrud.VideoDownloader',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.add_main_option(
            'url', ord('u'), GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
            N_('Prefill URL field'), 'URL')
        GLib.set_application_name(N_('Video Downloader'))
        self.version = version

    def _on_color_scheme_changed(self, value):
        style_manager = Adw.StyleManager.get_default()
        if value == 'system':
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)
        elif value == 'light':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif value == 'dark':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            assert False, ('invalid value for \'color-scheme\' property: %r' %
                           value)

    def do_startup(self):
        Adw.Application.do_startup(self)
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
        # Setup CSS
        css_uri = 'resource:///com/github/unrud/VideoDownloader/style.css'
        css_provider = Gtk.CssProvider()
        css_provider.load_from_file(Gio.File.new_for_uri(css_uri))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)
        # WORKAROUND: The `destroy` signal of `ApplicationWindow` doesn't work,
        # use the `window-removed` signal for shutdown instead
        self.connect('window-removed', lambda _, win: win.shutdown())

    def _new_window(self, url=''):
        win = Window(self)
        win.set_default_icon_name(self.props.application_id)
        model = win.model
        model.url = url
        # Apply/Bind settings
        self.settings.bind('download-folder', model, 'download-folder',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('prefer-mpeg', model, 'prefer-mpeg',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('automatic-subtitles', model, 'automatic-subtitles',
                           Gio.SettingsBindFlags.DEFAULT)
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
        win.present()

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
