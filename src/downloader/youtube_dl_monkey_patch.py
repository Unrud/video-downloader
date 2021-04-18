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

import subprocess

from youtube_dl.postprocessor.ffmpeg import FFmpegPostProcessor

real_popen = subprocess.Popen


def wrap_popen_ignore_stderr(*args, stderr=None, **kwargs):
    fwd_stderr = None if stderr == subprocess.PIPE else stderr
    p = real_popen(*args, stderr=fwd_stderr, **kwargs)
    real_communicate = p.communicate

    def wrap_communicate(*args, **kwargs):
        outs, errs = real_communicate(*args, **kwargs)
        if stderr == subprocess.PIPE:
            # Support for `encoding` etc. is not implemented
            errs = b''
        return outs, errs
    p.communicate = wrap_communicate
    return p


def with_popen_wrapper(f):
    '''Run function `f` with monkey-patched `subprocess.Popen`

    Not thread-safe and doesn't support recursion

    '''
    def wrap_f(*args, **kwargs):
        assert subprocess.Popen is real_popen
        subprocess.Popen = wrap_popen_ignore_stderr
        try:
            retval = f(*args, **kwargs)
        finally:
            assert subprocess.Popen is wrap_popen_ignore_stderr
            subprocess.Popen = real_popen
        return retval
    return wrap_f


def install_monkey_patches():
    # ffmpeg writes progress information to stderr, but youtube-dl captures it
    # by default. Overriding this behavior allows us to show activity while
    # converting audio to MP3 or finishing videos.
    FFmpegPostProcessor.run_ffmpeg_multiple_files = with_popen_wrapper(
        FFmpegPostProcessor.run_ffmpeg_multiple_files)
