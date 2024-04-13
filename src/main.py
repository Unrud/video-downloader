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

from gi.repository import Adw, Gio, GLib

from video_downloader.util import gobject_log
from video_downloader.util.connection import (
    CloseStack, SignalConnection, create_action)
from video_downloader.window import Window

N_ = gettext.gettext


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.github.unrud.VideoDownloader',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._cs = CloseStack()
        self.add_main_option(
            'url', ord('u'), GLib.OptionFlags.NONE, GLib.OptionArg.STRING,
            N_('Prefill URL field'), 'URL')
        GLib.set_application_name(N_('Video Downloader'))

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._cs.push(SignalConnection(
            self, 'shutdown', self._cs.close, no_args=True))
        self.settings = gobject_log(
            Gio.Settings.new(self.props.application_id))
        # Setup actions
        create_action(self, self._cs, 'new-window',
                      lambda _, param: self._new_window(param.get_string()),
                      parameter_type=GLib.VariantType('s'))
        create_action(self, self._cs, 'quit', self._quit, no_args=True)
        self._cs.push(SignalConnection(
            self, 'window-removed', lambda _, win: win.destroy()))

    def _quit(self):
        for win in self.get_windows():
            win.close()

    def _new_window(self, url=''):
        win = gobject_log(Window(self))
        win.set_default_icon_name(self.props.application_id)
        model = win.model
        model.url = url
        # Apply/Bind settings
        self.settings.bind('download-folder', model, 'download-folder',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('prefer-mpeg', model, 'prefer-mpeg', (
                               Gio.SettingsBindFlags.DEFAULT |
                               Gio.SettingsBindFlags.GET_NO_CHANGES))
        self.settings.bind('automatic-subtitles', model, 'automatic-subtitles',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('mode', model, 'mode', (
                               Gio.SettingsBindFlags.DEFAULT |
                               Gio.SettingsBindFlags.GET_NO_CHANGES))
        resolution = self.settings.get_uint('resolution')
        model.resolution = sorted(model.resolutions,
                                  key=lambda x: abs(x - resolution))[0]
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
    app = gobject_log(Application())
    return app.run(sys.argv)
