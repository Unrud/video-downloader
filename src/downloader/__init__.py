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
import functools
import os
import re
import signal
import subprocess
import sys
import traceback
import typing

from gi.repository import GLib

from video_downloader.util import g_log
from video_downloader.util.response import AsyncResponse, Response
from video_downloader.util.rpc import handle_rpc_request, rpc_response

MAX_RESOLUTION = 2**16-1

# RegEx for splitting lines because `bytes.splitlines` transforms
# `b'abc\n'` to `[b'abc']` instead of `[b'abc', b'']`
_SPLITLINES_RE = re.compile(rb'\r\n|\r|\n')


class Downloader:
    def __init__(self, handler):
        self._handler = handler
        self._process = None
        self._pending_response = None
        self._cancelled = False

    def shutdown(self):
        self._handler = None
        if self._process:
            self._finish_process_and_kill_pgrp()

    def cancel(self):
        if not self._cancelled:
            self._process.terminate()
        self._cancelled = True
        if self._pending_response:
            self._pending_response.cancel()

    def start(self):
        assert not self._process
        extra_env = {'PYTHONPATH': os.pathsep.join(sys.path)}
        # Start child process in its own process group to shield it from
        # signals by terminals (e.g. SIGINT) and to identify remaning children.
        # yt-dlp doesn't kill ffmpeg and other subprocesses on error.
        self._process = subprocess.Popen(
            [sys.executable, '-u', '-m', 'video_downloader.downloader'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env={**os.environ, **extra_env},
            universal_newlines=True, preexec_fn=os.setpgrp)
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
        self._cancelled = False
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

    def _pending_response_callback(self, process, request_line, response):
        assert self._pending_response is response
        self._pending_response = None
        if response.cancelled:
            self.cancel()
        else:
            self._send_response(process, request_line, response.result)

    @staticmethod
    def _send_response(process, request_line, result):
        try:
            print(rpc_response(result), file=process.stdin, flush=True)
        except Exception:
            g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                  'failed request %r\n%s', request_line,
                  traceback.format_exc())
            process.terminate()

    def _on_process_stdout(self, fd, condition, process):
        # Don't use `process.stdout.read` because of O_NONBLOCK (see `start`)
        s = process.stdout.buffer.read()
        pipe_closed = not s
        process.stdout_remainder += s
        *lines, process.stdout_remainder = _SPLITLINES_RE.split(
            process.stdout_remainder)
        if self._process is not process:
            return not pipe_closed
        failure = False
        line: typing.AnyStr
        for line in filter(None, lines):  # Filter empty lines
            try:
                line = line.decode(process.stdout.encoding)
                if self._pending_response:
                    raise RuntimeError('request during pending request')
                result = handle_rpc_request(
                    HandlerInterface, self._handler, line)
            except Exception:
                g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                      'failed request %r\n%s', line, traceback.format_exc())
                failure = True
                break
            if isinstance(result, AsyncResponse):
                self._pending_response = result
                self._pending_response.add_done_callback(functools.partial(
                    self._pending_response_callback, self._process, line))
            else:
                self._send_response(self._process, line, result)
        if pipe_closed and process.stdout_remainder:
            g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                  'incomplete request %r', process.stdout_remainder)
            failure = True
        if pipe_closed or failure:
            returncode = self._finish_process_and_kill_pgrp()
            if self._pending_response:
                self._pending_response.cancel()
            self._handler.on_finished(returncode == 0 and not failure)
        return not pipe_closed

    def _on_process_stderr(self, fd, condition, process):
        # Don't use `process.stderr.read` because of O_NONBLOCK (see `start`)
        s = process.stderr.buffer.read()
        pipe_closed = not s
        process.stderr_remainder += s
        if pipe_closed:
            process.stderr_remainder += b'\n'
        *lines, process.stderr_remainder = _SPLITLINES_RE.split(
            process.stderr_remainder)
        for line in filter(None, lines):  # Filter empty lines
            # Don't use `errors='strict'` because programs might write garbage
            # to stderr
            line = line.decode(process.stderr.encoding, errors='replace')
            g_log('yt-dlp', GLib.LogLevelFlags.LEVEL_DEBUG, '%s', line)
            if self._process is process:
                self._handler.on_pulse()
        return not pipe_closed


class HandlerInterface:
    def get_download_dir(self) -> Response[str]:
        raise NotImplementedError

    def get_prefer_mpeg(self) -> Response[bool]:
        raise NotImplementedError

    def get_automatic_subtitles(self) -> Response[typing.List[str]]:
        raise NotImplementedError

    def get_url(self) -> Response[str]:
        raise NotImplementedError

    def get_mode(self) -> Response[str]:
        raise NotImplementedError

    def get_resolution(self) -> Response[int]:
        raise NotImplementedError

    def on_playlist_request(self) -> Response[bool]:
        raise NotImplementedError

    #                                                   user password
    def on_login_request(self) -> Response[typing.Tuple[str, str]]:
        raise NotImplementedError

    #                                         password
    def on_password_request(self) -> Response[str]:
        raise NotImplementedError

    def on_error(self, msg: str) -> Response[None]:
        raise NotImplementedError

    def on_progress(self, filename: str, progress: float, bytes_: int,
                    bytes_total: int, eta: int, speed: int) -> Response[None]:
        raise NotImplementedError

    def on_download_start(self, playlist_index: int, playlist_count: int,
                          title: str) -> Response[None]:
        raise NotImplementedError

    #                                                 lock acquired
    def on_download_lock(self, name: str) -> Response[bool]:
        """Lock gets released by `on_download_finished` or process termination.
           It's not allowed to hold more than one lock at a time."""
        raise NotImplementedError

    def on_download_thumbnail(self, thumbnail: str) -> Response[None]:
        raise NotImplementedError

    def on_download_finished(self, filename: str) -> Response[None]:
        raise NotImplementedError

    def on_pulse(self) -> Response[None]:
        raise NotImplementedError

    def on_finished(self, success: bool) -> Response[None]:
        raise NotImplementedError
