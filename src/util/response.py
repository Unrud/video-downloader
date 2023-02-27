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

import typing

from video_downloader.util.connection import Closable

_R = typing.TypeVar('R')


class AsyncResponse(typing.Generic[_R], Closable):
    def __init__(self) -> None:
        super().__init__()
        self.__done = False
        self.__cancelled = False
        self.__result = None

    @property
    def done(self) -> bool:
        return self.__done

    @property
    def cancelled(self) -> bool:
        return self.__cancelled

    @property
    def result(self) -> typing.Optional[_R]:
        return self.__result

    def add_done_callback(self, callback: typing.Callable[
                              ["AsyncResponse[_R]"], None]) -> None:
        self.add_close_callback(callback, self)

    def set_result(self, result: _R) -> None:
        assert not self.done, 'done'
        self.__result = result
        self.__done = True
        self.close()

    def cancel(self) -> None:
        assert not self.done, 'done'
        self.close()

    def chain(self, chained_response: "AsyncResponse[_R]"
              ) -> "AsyncResponse[_R]":
        def callbackChain(response):
            assert response.done
            if not response.cancelled:
                chained_response.set_result(response.result)
            elif not chained_response.cancelled:
                chained_response.cancel()
        self.add_done_callback(callbackChain)

        def callbackCancel(chained_response):
            assert chained_response.done
            if not self.done:
                assert chained_response.cancelled
                self.cancel()
        chained_response.add_done_callback(callbackCancel)

    def close(self):
        if not self.done:
            self.__cancelled = True
            self.__done = True
        super().close()


Response = typing.Union[_R, AsyncResponse[_R]]
