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

import json
import os
import select
import subprocess
import sys
import threading
import typing

from video_downloader import pkgdatadir

MAX_RESOLUTION = 2**32


class Downloader(threading.Thread):
    def __init__(self, handler):
        super().__init__()
        self.process = None
        self.handler = handler
        self.daemon = True

    def cancel(self):
        self.process.terminate()
        self.process.wait()

    def start(self):
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = pythonpath = (
            pkgdatadir + (os.pathsep if pythonpath else "") + pythonpath)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "video_downloader.downloader"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env,
            universal_newlines=True, start_new_session=True)
        return super().start()

    def run(self):
        while True:
            _, _, _ = select.select([self.process.stdout], [], [])
            s = self.process.stdout.readline()
            if s:
                try:
                    request = json.loads(s)
                except json.JSONDecodeError:
                    print("ERROR: Invalid request: %r" % s, file=sys.stderr)
                    self.process.kill()
                    break
                method = getattr(self.handler, request["method"])
                result = method(*request["args"])
                try:
                    print(json.dumps({"result": result}),
                          flush=True, file=self.process.stdin)
                except BrokenPipeError:
                    self.process.kill()
                    break
            else:
                break
        retcode = self.process.wait()
        self.handler.on_finished(retcode == 0)


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

    def on_progress(self, filename: str, progress: int, bytes_: int,
                    bytes_total: int, eta: int, speed: int):
        raise NotImplementedError

    def on_playlist_progress(self, playlist_index: int, playlist_count: int):
        raise NotImplementedError

    def on_finished(self, success: bool):
        raise NotImplementedError
