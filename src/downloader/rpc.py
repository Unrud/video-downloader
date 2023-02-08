# Copyright (C) 2023 Unrud <unrud@outlook.com>
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

import functools
import json


class RpcClient:
    def __init__(self, output_file, input_file=None):
        self._output_file = output_file
        self._input_file = input_file

    def _rpc(self, name, *args):
        print(json.dumps({'method': name, 'args': args}),
              file=self._output_file, flush=True)
        if self._input_file is None:
            return None
        answer = json.loads(self._input_file.readline())
        return answer['result']

    def __getattr__(self, name):
        return functools.partial(self._rpc, name)


def handle_rpc_request(interface, implementation, json_request):
    request = json.loads(json_request)
    # Execute request
    return getattr(implementation, request['method'])(*request['args'])
