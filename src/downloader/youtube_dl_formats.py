# downloader/youtube_dl_formats.py
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

import youtube_dl

from video_downloader.downloader import MAX_RESOLUTION


def sort_formats(formats, resolution=MAX_RESOLUTION, prefer_mpeg=False):
    """Mostly copied from youtube_dl.extractor.common._sort_formats"""
    def _formats_key(f):
        preference = f.get('preference')
        if preference is None:
            preference = 0
            if f.get('ext') in ['f4f', 'f4m']:  # Not yet supported
                preference -= 0.5

        protocol = (f.get('protocol') or
                    youtube_dl.extractor.common.determine_protocol(f))
        proto_preference = (0 if protocol in ['http', 'https']
                            else (-0.5 if protocol == 'rtsp' else -0.1))

        if f.get('vcodec') == 'none':  # audio only
            preference -= 50
            if prefer_mpeg:
                ORDER = ['webm', 'ogg', 'opus', 'aac', 'm4a', 'mp3']
            else:
                ORDER = ['aac', 'm4a', 'mp3', 'webm', 'ogg', 'opus']
            ext_preference = 0
            try:
                audio_ext_preference = ORDER.index(f['ext'])
            except ValueError:
                audio_ext_preference = -1
        else:
            if f.get('acodec') == 'none':  # video only
                preference -= 40
            if prefer_mpeg:
                ORDER = ['flv', 'webm', 'mp4']
            else:
                ORDER = ['flv', 'mp4', 'webm']
            try:
                ext_preference = ORDER.index(f['ext'])
            except ValueError:
                ext_preference = -1
            audio_ext_preference = 0

        width = f.get('width') if f.get('width') is not None else -1
        height = f.get('height') if f.get('height') is not None else -1
        if width >= 0 and (height < 0 or width < height):
            # Vertical video
            norm_width, norm_height = height, width
        else:
            norm_width, norm_height = width, height
        if norm_height >= 0:
            resolution_diff = MAX_RESOLUTION - abs(norm_height - resolution)
        else:
            resolution_diff = -1

        return (
            preference,
            (f.get('language_preference')
             if f.get('language_preference') is not None else -1),
            resolution_diff,
            f.get('quality') if f.get('quality') is not None else -1,
            f.get('fps') if f.get('fps') is not None else -1,
            ext_preference,
            audio_ext_preference,
            f.get('tbr') if f.get('tbr') is not None else -1,
            f.get('filesize') if f.get('filesize') is not None else -1,
            f.get('vbr') if f.get('vbr') is not None else -1,
            f.get('abr') if f.get('abr') is not None else -1,
            norm_height,
            norm_width,
            proto_preference,
            (f.get('filesize_approx')
             if f.get('filesize_approx') is not None else -1),
            (f.get('source_preference')
             if f.get('source_preference') is not None else -1),
            f.get('format_id') if f.get('format_id') is not None else '',
        )
    formats.sort(key=_formats_key)
