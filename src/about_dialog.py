# Copyright (C) 2020 Unrud <unrud@outlook.com>
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

import os
import platform
import traceback

from gi.repository import Adw, GLib, Gtk

from video_downloader.util import g_log


@Gtk.Template(resource_path='/com/github/unrud/VideoDownloader/'
                            'about_dialog.ui')
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = 'VideoDownloaderAboutDialog'

    def __init__(self, parent, version):
        try:
            import yt_dlp
            yt_dlp_version = str(yt_dlp.version.__version__)
        except Exception:
            g_log(None, GLib.LogLevelFlags.LEVEL_WARNING, '%s',
                  traceback.format_exc())
            yt_dlp_version = None
        system_info = '\n'.join([
            'OS: %s' % (GLib.get_os_info('PRETTY_NAME')),
            '',
            'Libraries:',
            *('\t%s %s' % (name, version) for name, version in [
                  ('Python', platform.python_version()),
                  *((name, '%d.%d.%d' % (lib.MAJOR_VERSION, lib.MINOR_VERSION,
                                         lib.MICRO_VERSION))
                    for name, lib in [('GLib', GLib), ('Gtk', Gtk),
                                      ('Libadwaita', Adw)]),
                  ('video-downloader', version),
                  ('yt-dlp', yt_dlp_version),
              ] if version),
            '',
            'Env:',
            *('\t%s=%s' % (name, os.environ[name]) for name in [
                  'LANGUAGES',
                  'LC_ALL',
                  'LC_MESSAGES',
                  'LANG',
                  'G_MESSAGES_DEBUG',
              ] if name in os.environ)
        ])
        super().__init__(version=version, system_information=system_info)
        self.set_transient_for(parent)
