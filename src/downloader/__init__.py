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

import contextlib
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import traceback
import typing

from gi.repository import GLib

from video_downloader.util import g_log

MAX_RESOLUTION = 2**16-1


class Downloader:
    def __init__(self, handler):
        self._handler = handler
        self._process = None
        # Use regex to split lines because `bytes.splitlines` transforms
        # `b'abc\n'` to `[b'abc']` instead of `[b'abc', b'']`
        self._splitlines_re = re.compile(rb'\r\n|\r|\n')

    def shutdown(self):
        if self._process:
            self._finish_process_and_kill_pgrp()

    def cancel(self):
        self._process.terminate()

    def start(self):
        assert not self._process
        env = os.environ.copy()
        env['PYTHONPATH'] = os.pathsep.join(filter(None, [
            os.path.join(__file__, *[os.pardir]*3), env.get('PYTHONPATH')]))
        # Start child process in its own process group to shield it from
        # signals by terminals (e.g. SIGINT) and to identify remaning children.
        # yt-dlp doesn't kill ffmpeg and other subprocesses on error.
        self._process = subprocess.Popen(
            [sys.executable, '-u', '-m', 'video_downloader.downloader'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, universal_newlines=True,
            preexec_fn=os.setpgrp)
        # WARNING: O_NONBLOCK can break mult ibyte decoding and line splitting
        # under rare circumstances.
        # E.g. when the buffer only includes the first byte of a multi byte
        # UTF-8 character, TextIOWrapper would normally block until all bytes
        # of the character are read. This does not work with O_NONBLOCK, and it
        # raises UnicodeDecodeError instead.
        # E.g. when the buffer only includes `b'\r'`, TextIOWrapper would
        # normally block to read the next byte and check if it's `b'\n'`.
        # This does not work with O_NONBLOCK, and it gets transformed to `'\n'`
        # directly. The line ending `b'\r\n'` will be transformed to `'\n\n'`.
        fcntl.fcntl(self._process.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self._process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
        self._process.stdout_remainder = self._process.stderr_remainder = b''
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT_IDLE, self._process.stdout.fileno(),
            GLib.IOCondition.IN, self._on_process_stdout, self._process)
        GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT_IDLE, self._process.stderr.fileno(),
            GLib.IOCondition.IN, self._on_process_stderr, self._process)

    def _finish_process_and_kill_pgrp(self):
        assert self._process
        process, self._process = self._process, None
        try:
            # Terminate process gracefully so it can delete temporary files
            process.terminate()
            process.wait()
        except BaseException:  # including SystemExit and KeyboardInterrupt
            process.kill()
            process.wait()
        finally:
            # Kill remaining children identified by process group
            with contextlib.suppress(OSError):
                os.killpg(process.pid, signal.SIGKILL)
        return process.returncode

    def _on_process_stdout(self, fd, condition, process):
        # Don't use `process.stdout.read` because of O_NONBLOCK (see `start`)
        s = process.stdout.buffer.read()
        pipe_closed = not s
        process.stdout_remainder += s
        *lines, process.stdout_remainder = self._splitlines_re.split(
            process.stdout_remainder)
        if self._process is not process:
            return not pipe_closed
        failure = False
        line: typing.AnyStr
        for line in filter(None, lines):  # Filter empty lines
            try:
                line = line.decode(process.stdout.encoding)
                request = json.loads(line)
                method = getattr(self._handler, request['method'])
                result = method(*request['args'])
                print(json.dumps({'result': result}),
                      file=process.stdin, flush=True)
            except Exception:
                g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                      'failed request %r\n%s', line, traceback.format_exc())
                failure = True
                break
        if pipe_closed and process.stdout_remainder:
            g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                  'incomplete request %r', process.stdout_remainder)
            failure = True
        if pipe_closed or failure:
            returncode = self._finish_process_and_kill_pgrp()
            self._handler.on_finished(returncode == 0 and not failure)
        return not pipe_closed

    def _on_process_stderr(self, fd, condition, process):
        # Don't use `process.stderr.read` because of O_NONBLOCK (see `start`)
        s = process.stderr.buffer.read()
        pipe_closed = not s
        process.stderr_remainder += s
        if pipe_closed:
            process.stderr_remainder += b'\n'
        *lines, process.stderr_remainder = self._splitlines_re.split(
            process.stderr_remainder)
        for line in filter(None, lines):  # Filter empty lines
            # Don't use `errors='strict'` because programs might write garbage
            # to stderr
            line = line.decode(process.stderr.encoding, errors='replace')
            g_log('yt-dlp', GLib.LogLevelFlags.LEVEL_DEBUG, '%s', line)
            if self._process is process:
                self._handler.on_pulse()
        return not pipe_closed


class Handler:
    def get_download_dir(self) -> str:
        raise NotImplementedError

    def get_prefer_mpeg(self) -> bool:
        raise NotImplementedError

    def get_automatic_subtitles(self) -> typing.List[str]:
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

    def on_progress(self, filename: str, progress: float, bytes_: int,
                    bytes_total: int, eta: int, speed: int):
        raise NotImplementedError

    def on_download_start(self, playlist_index: int, playlist_count: int,
                          title: str):
        raise NotImplementedError

    def on_download_thumbnail(self, thumbnail: str):
        raise NotImplementedError

    def on_download_finished(self, filename):
        raise NotImplementedError

    def on_pulse(self):
        raise NotImplementedError

    def on_finished(self, success: bool):
        raise NotImplementedError
