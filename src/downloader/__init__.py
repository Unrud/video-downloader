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

import contextlib
import fcntl
import json
import os
import subprocess
import sys
import traceback
import typing
from gi.repository import GLib

from video_downloader.util import g_log

MAX_RESOLUTION = 2**16


class Downloader:
    def __init__(self, handler):
        self._handler = handler
        self._process = None

    def cancel(self):
        self._process.terminate()

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
        fcntl.fcntl(self._process.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self._process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
        self._process.stdout_remainder = self._process.stderr_remainder = ''
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT_IDLE, self._process.stdout.fileno(),
            GLib.IOCondition.IN, self._on_process_stdout)
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT_IDLE, self._process.stderr.fileno(),
            GLib.IOCondition.IN, self._on_process_stderr, self._process)

    def _on_process_stdout(self, *args):
        s = self._process.stdout.read()
        self._process.stdout_remainder += s
        *lines, self._process.stdout_remainder = \
            self._process.stdout_remainder.split('\n')
        for line in lines:
            try:
                request = json.loads(line)
                method = getattr(self._handler, request['method'])
                result = method(*request['args'])
                with contextlib.suppress(BrokenPipeError):
                    print(json.dumps({'result': result}),
                          flush=True, file=self._process.stdin)
            except Exception:
                g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                      'failed request %r\n%s', line, traceback.format_exc())
                self._process.kill()
        if not s:
            if self._process.stdout_remainder:
                g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                      'incomplete request %r', self._process.stdout_remainder)
            # Unset self._process first for self._on_process_stderr
            process, self._process = self._process, None
            self._handler.on_finished(process.wait() == 0)
            return False
        return True

    def _on_process_stderr(self, fd, condition, process):
        s = process.stderr.read()
        process.stderr_remainder += s or '\n'
        *lines, process.stderr_remainder = process.stderr_remainder.split('\n')
        for line in filter(None, lines):
            g_log('youtube-dl', GLib.LogLevelFlags.LEVEL_DEBUG, '%s', line)
        if self._process is process:
            self._handler.on_pulse()
        return bool(s)


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
