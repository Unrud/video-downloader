# utils.py
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

from video_downloader import WRAPLENGTH


def wrap_text(s, wraplength=WRAPLENGTH):
    lines = s.split("\n")
    new_lines = []
    for _, line in enumerate(lines):
        while True:
            wrap_start = wrap_end = wraplength
            if len(line) > wrap_start:
                p = line[:wrap_start].rfind(" ")
                if p >= 0:
                    wrap_start = p
                    wrap_end = p + 1
            new_lines.append(line[:wrap_start])
            line = line[wrap_end:]
            if not line:
                break
    return "\n".join(new_lines)
