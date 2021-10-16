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

import io
import subprocess
import sys
import threading


def _tee(fin, *fouts):
    '''Read from `fin` and write to all `fouts`'''
    while True:
        b = fin.read(1)
        if not b:
            break
        for fout in fouts:
            fout.write(b)


class PatchedPopen(subprocess.Popen):

    def communicate(self, *args, **kwargs):
        '''When processe's stderr gets redirected by `subprocess.PIPE`
           duplicate it to `sys.stderr`
        '''
        if not self.stderr:
            return super().communicate(*args, **kwargs)
        if hasattr(self.stderr, 'encoding'):
            errs_buf = io.StringIO()
            sys_stderr = sys.stderr
        else:
            errs_buf = io.BytesIO()
            sys_stderr = sys.stderr.buffer
        tee_thread = threading.Thread(
            target=_tee, args=(self.stderr, sys_stderr, errs_buf), daemon=True)
        self.stderr = None
        tee_thread.start()
        outs, _ = super().communicate(*args, **kwargs)
        tee_thread.join()
        return outs, errs_buf.getvalue()


def install_monkey_patches():
    # ffmpeg writes progress information to stderr, but yt-dlp captures it
    # by default. Overriding this behavior allows us to show activity while
    # converting audio to MP3 or finishing videos.
    subprocess.Popen = PatchedPopen
