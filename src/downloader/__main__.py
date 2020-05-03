# downloader/__main__.py
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

import sys

import youtube_dl

from video_downloader.downloader.youtube_dl_slave import YoutubeDLSlave

if __name__ == '__main__':
    try:
        YoutubeDLSlave()
    except youtube_dl.utils.DownloadError:
        sys.exit(1)
