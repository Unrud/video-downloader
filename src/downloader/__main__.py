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

import os
import signal
import sys

from video_downloader.util.rpc import RpcClient


if __name__ == '__main__':
    # Exit gracefully on SIGTERM to allow cleanup code to run
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))
    # Duplicate stdin and stdout for exclusive usage with handler.
    # The handler waits for stdin and stdout to be closed. The fds must not
    # be closed before the process exits to avoid race.
    input_file = os.fdopen(os.dup(sys.stdin.fileno()), 'r', closefd=False)
    output_file = os.fdopen(os.dup(sys.stdout.fileno()), 'w', closefd=False)
    # Prevent leaking the fds to children that might remain after this process
    # exits
    os.set_inheritable(input_file.fileno(), False)
    os.set_inheritable(output_file.fileno(), False)
    # Redirect stdin and stdout to /dev/null to prevent interferences
    with open(os.devnull, 'r+') as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno(), inheritable=True)
        os.dup2(devnull.fileno(), sys.stdout.fileno(), inheritable=True)
    handler = RpcClient(output_file, input_file)
    try:
        from video_downloader.downloader.yt_dlp_monkey_patch import (
            install_monkey_patches)
        install_monkey_patches()

        import yt_dlp
        from video_downloader.downloader.yt_dlp_slave import YoutubeDLSlave
        try:
            YoutubeDLSlave(handler)
        except yt_dlp.utils.DownloadError:
            sys.exit(1)
    except Exception as e:
        handler.on_error('%s: %s' % (type(e).__name__, e))
        raise
