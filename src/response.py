from contextlib import asynccontextmanager
from typing import Callable

from .asgi_types import HttpSendCallable, HttpSendEvent
from .headers import HeadersImmutable, HeadersMutable

type DisconnectFlag = Callable[[], bool]


class ResponseException(Exception):
    pass


class Response:
    def __init__(self, send: HttpSendCallable, disconnected: DisconnectFlag) -> None:
        self.headers = HeadersMutable()
        self._state = "http.response"
        self._sender = send
        self._disconnected = disconnected
        self._status = 200

    def status(self, status: int) -> None:
        if self._state != "http.response":
            raise ResponseException(f"Invalid state for http.response: {self._state}")
        self._status = status

    async def header(self) -> None:
        if self._state != "http.response":
            raise ResponseException(f"Invalid state for http.response.start: {self._state}")
        self.headers = HeadersImmutable.load(self.headers)
        await self._send({"type": "http.response.start", "status": self._status, "headers": self.headers.serialize()})
        self._state = "http.response.start"

    async def body(self, body: bytes, more_body: bool = False) -> None:
        if self._state == "http.response":
            await self.header()
        if self._state == "http.response.start":
            if more_body:
                await self._send({"type": "http.response.body", "body": body, "more_body": True})
                self._state = "http.response.body"
            else:
                await self._send({"type": "http.response.body", "body": body})
                self._state = "http.response.closed"
        elif self._state == "http.response.body":
            if more_body:
                await self._send({"type": "http.response.body", "body": body, "more_body": True})
            else:
                await self._send({"type": "http.response.body", "body": body})
                self._state = "http.response.closed"
        else:
            raise ResponseException(f"Invalid state for http.response.body: {self._state}")

    async def close(self) -> None:
        if self._state != "http.response.closed":
            await self.body(b"")
        self._state = "http.response.closed"

    async def _send(self, event: HttpSendEvent) -> None:
        if self._disconnected():
            raise ResponseException("Connection closed")
        try:
            await self._sender(event)
        except (OSError, RuntimeError) as e:
            raise ResponseException("Connection closed") from e


@asynccontextmanager
async def response(send: HttpSendCallable, disconnected: DisconnectFlag):
    response = Response(send, disconnected)
    try:
        yield response
    finally:
        await response.close()
