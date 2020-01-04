# downloader/__init__.py
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

import fcntl
import json
import os
import subprocess
import sys
import typing
from gi.repository import GLib

from video_downloader.util import g_log

MAX_RESOLUTION = 2**16


class Downloader:
    def __init__(self, handler):
        self._handler = handler
        self._process = None
        self._process_stderr_rem = ''

    def cancel(self):
        if self._process:
            self._process.terminate()
            self._process.wait()

    def start(self):
        assert not self._process
        env = os.environ.copy()
        env['PYTHONPATH'] = os.pathsep.join(filter(None, [
            os.path.join(__file__, *[os.pardir]*3), env.get('PYTHONPATH')]))
        self._process = subprocess.Popen(
            [sys.executable, '-u', '-m', 'video_downloader.downloader'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, universal_newlines=True,
            start_new_session=True)
        fcntl.fcntl(self._process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT_IDLE, self._process.stdout.fileno(),
            GLib.IOCondition.IN, self._on_process_stdout)
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT_IDLE, self._process.stderr.fileno(),
            GLib.IOCondition.IN, self._on_process_stderr)

    def _on_process_stdout(self, *args):
        s = self._process.stdout.readline()
        if not s:
            self._handler.on_finished(self._process.wait() == 0)
            self._process = None
            return False
        try:
            request = json.loads(s)
        except json.JSONDecodeError:
            print('ERROR: Invalid request: %r' % s, file=sys.stderr)
            self._process.kill()
            return True
        method = getattr(self._handler, request['method'])
        result = method(*request['args'])
        try:
            print(json.dumps({'result': result}),
                  flush=True, file=self._process.stdin)
        except BrokenPipeError:
            self._process.kill()
        return True

    def _on_process_stderr(self, *args):
        if self._process:
            self._handler.on_pulse()
            self._process_stderr_rem += self._process.stderr.read()
        else:
            self._process_stderr_rem += '\n'
        *lines, self._process_stderr_rem = self._process_stderr_rem.split('\n')
        for line in filter(None, lines):
            g_log('youtube-dl', GLib.LogLevelFlags.LEVEL_DEBUG, '%s', line)
        return bool(self._process)


class Handler:
    def get_target_dir(self) -> str:
        raise NotImplementedError

    def get_url(self) -> str:
        raise NotImplementedError

    def get_mode(self) -> str:
        raise NotImplementedError

    def get_resolution(self) -> int:
        raise NotImplementedError

    def on_playlist_request(self) -> bool:
        raise NotImplementedError

    #                                          user password
    def on_login_request(self) -> typing.Tuple[str, str]:
        raise NotImplementedError

    #                                     password
    def on_videopassword_request(self) -> str:
        raise NotImplementedError

    def on_error(self, msg: str):
        raise NotImplementedError

    def on_load_progress(self, filename: str, progress: float, bytes_: int,
                         bytes_total: int, eta: int, speed: int):
        raise NotImplementedError

    def on_progress(self, playlist_index: int, playlist_count: int, title: str,
                    thumbnail: str):
        raise NotImplementedError

    def on_pulse(self):
        raise NotImplementedError

    def on_finished(self, success: bool):
        raise NotImplementedError
