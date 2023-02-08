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
import subprocess
import sys
import traceback
import typing

from gi.repository import GLib

from video_downloader.downloader.rpc import RpcClient, handle_rpc_request
from video_downloader.util import g_log

MAX_RESOLUTION = 2**16-1

# RegEx for splitting lines because `bytes.splitlines` transforms
# `b'abc\n'` to `[b'abc']` instead of `[b'abc', b'']`
_SPLITLINES_RE = re.compile(rb'\r\n|\r|\n')


class Downloader:
    def __init__(self, handler):
        self._handler = handler
        self._process = None
        self._process_handler = None
        self._pending_response = None

    def shutdown(self):
        self._handler = None
        if self._process:
            self._finish_process()

    def cancel(self):
        with contextlib.suppress(BrokenPipeError):
            self._process_handler.cancel()
        if self._pending_response:
            self._pending_response._finish()

    def start(self):
        assert not self._process and not self._process_handler
        extra_env = {'PYTHONPATH': os.pathsep.join(sys.path)}
        process_control_output_fd, process_control_input_fd = os.pipe()
        process_control_input_file = os.fdopen(process_control_input_fd, 'w')
        try:
            process_handler = RpcClient(process_control_input_file)
            sandbox = []
            if os.path.isfile('/.flatpak-info'):
                download_dir = self._handler.get_download_dir()
                sandbox += ['flatpak-spawn', '--directory=/', '--sandbox',
                            '--sandbox-expose-path=%s' % download_dir,
                            '--forward-fd=%d' % process_control_output_fd,
                            *('--env=%s=%s' % (key, value)
                              for key, value in extra_env.items())]
            self._process = subprocess.Popen(
                [*sandbox, sys.executable, '-u', '-m',
                 'video_downloader.downloader',
                 '--control-fd=%d' % process_control_output_fd],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env={**os.environ, **extra_env},
                universal_newlines=True, pass_fds=(process_control_output_fd,))
        except BaseException:
            process_control_input_file.close()
            raise
        finally:
            os.close(process_control_output_fd)
        self._process_handler = process_handler
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

    def _finish_process(self):
        assert self._process and self._process_handler
        process, process_handler = self._process, self._process_handler
        self._process = self._process_handler = None
        with contextlib.suppress(BrokenPipeError):
            process_handler.shutdown()
        return process.wait()

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
            if isinstance(result, _AsyncResponse):
                self._pending_response = result
            else:
                self._pending_response = _AsyncResponse()
            self._pending_response._downloader = self
            self._pending_response._request_line = line
            if not isinstance(result, _AsyncResponse):
                self._pending_response.respond(result)
        if pipe_closed and process.stdout_remainder:
            g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                  'incomplete request %r', process.stdout_remainder)
            failure = True
        if pipe_closed or failure:
            returncode = self._finish_process()
            if self._pending_response:
                self._pending_response._finish()
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


_R = typing.TypeVar('R')


class _AsyncResponse(typing.Generic[_R]):
    def __init__(self, done_callback=None):
        self._done_callback = done_callback
        self._downloader = None
        self._request_line = None

    def _finish(self):
        assert self._downloader and self._downloader._pending_response is self
        self._downloader._pending_response = None
        if self._done_callback is not None:
            self._done_callback()

    def respond(self, result: _R) -> None:
        try:
            print(json.dumps({'result': result}),
                  file=self._downloader._process.stdin, flush=True)
        except Exception:
            g_log(None, GLib.LogLevelFlags.LEVEL_CRITICAL,
                  'failed request %r\n%s', self._request_line,
                  traceback.format_exc())
            self._downloader._process.terminate()
        self._finish()


class HandlerInterface:
    AsyncResponse = _AsyncResponse
    Response = typing.Union[_R, AsyncResponse[_R]]

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
