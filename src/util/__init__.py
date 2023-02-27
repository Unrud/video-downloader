# Copyright (C) 2019-2020 Unrud <unrud@outlook.com>
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

import locale
import os

from gi.repository import GLib


def gobject_log(obj, info=None):
    DOMAIN = 'gobject-ref'
    LEVEL = GLib.LogLevelFlags.LEVEL_DEBUG
    name = repr(obj)
    if info:
        name += ' (' + str(info) + ')'
    g_log(DOMAIN, LEVEL, 'Create %s', name)
    obj.weak_ref(g_log, DOMAIN, LEVEL, 'Destroy %s', name)
    return obj


def g_log(domain, log_level, format_string, *args):
    fields = GLib.Variant('a{sv}', {
        'MESSAGE': GLib.Variant('s', format_string % args)})
    GLib.log_variant(domain, log_level, fields)


def languages_from_locale():
    locale_languages = []
    for envar in ['LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG']:
        val = os.environ.get(envar)
        if val:
            locale_languages.extend(val.split(':'))
            break
    if 'C' not in locale_languages:
        locale_languages.append('C')
    languages = []
    for lang in locale_languages:
        lang = locale.normalize(lang)
        for sep in ['@', '.', '_']:
            lang = lang.split(sep, maxsplit=1)[0]
        if lang == 'C':
            lang = 'en'
        if lang not in languages:
            languages.append(lang)
    return languages
