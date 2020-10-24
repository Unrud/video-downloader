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

import functools
import json
import signal
import sys


class Handler:
    def _rpc(self, name, *args):
        print(json.dumps({'method': name, 'args': args}), flush=True)
        answer = json.loads(sys.stdin.readline())
        return answer['result']

    def __getattr__(self, name):
        return functools.partial(self._rpc, name)


if __name__ == '__main__':
    # Exit gracefully on SIGTERM to allow cleanup code to run
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))
    handler = Handler()
    try:
        import youtube_dl

        from video_downloader.downloader.youtube_dl_monkey_patch import (
            install_monkey_patches)
        from video_downloader.downloader.youtube_dl_slave import YoutubeDLSlave

        install_monkey_patches()
        try:
            YoutubeDLSlave(handler)
        except youtube_dl.utils.DownloadError:
            sys.exit(1)
    except Exception as e:
        handler.on_error('%s: %s' % (type(e).__name__, e))
        raise
