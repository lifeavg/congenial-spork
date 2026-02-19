import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Literal, Protocol, Self, override

from .asgi_types import HttpReceiveCallable
from .async_spooled_stream import AsyncSpoolStream


class StreamReceive(Protocol):
    async def get(self) -> bytes | None: ...
    def is_connected(self) -> bool: ...
    async def wait_disconnect(self) -> Literal[True]: ...
    @classmethod
    @asynccontextmanager
    async def listen(cls, receive: HttpReceiveCallable) -> AsyncGenerator[Self, None]:
        yield cls()

    def __aiter__(self) -> AsyncIterator[bytes]: ...

class _StreamReceiveBase:
    def __init__(self) -> None:
        self._disconnected = asyncio.Event()

    async def get(self) -> bytes | None:
        return await self._receive()

    def is_connected(self) -> bool:
        return self._disconnected.is_set()

    async def wait_disconnect(self) -> Literal[True]:
        return await self._disconnected.wait()

    async def _listener(self, receive: HttpReceiveCallable):
        body_consumed = False
        while True:
            event = await receive()
            if event["type"] == "http.request":
                body = event.get("body")
                if body:
                    await self._send(body)
                body_consumed = not event.get("more_body", False)
                if body_consumed:
                    await self._send(None)
            elif event["type"] == "http.disconnect":
                if not body_consumed:
                    body_consumed = True
                    await self._send(None)
                self._disconnected.set()
                break

    @classmethod
    @asynccontextmanager
    async def listen(cls, receive: HttpReceiveCallable) -> AsyncGenerator[Self, None]:
        stream = cls()
        listen_task = asyncio.create_task(stream._listener(receive))
        try:
            yield stream
        finally:
            listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await listen_task

    async def _send(self, data: bytes | None) -> None:
        raise NotImplementedError()

    async def _receive(self) -> bytes | None:
        raise NotImplementedError()

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> bytes:
        chunk = await self._receive()
        if chunk is None:
            raise StopAsyncIteration()
        return chunk


class StreamReceiveQueued(_StreamReceiveBase):
    def __init__(self) -> None:
        super().__init__()
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=16)

    @override
    async def _receive(self) -> bytes | None:
        return await self._queue.get()

    @override
    async def _send(self, data: bytes | None) -> None:
        await self._queue.put(data)


class StreamReceiveSpooled(_StreamReceiveBase):
    def __init__(self, stream: AsyncSpoolStream) -> None:
        super().__init__()
        self._stream: AsyncSpoolStream = stream
        self.read_chunk = 1024

    @override
    async def _receive(self) -> bytes | None:
        data = await self._stream.read()
        if not data:
            return None

    @override
    async def _send(self, data: bytes | None) -> None:
        if data is not None:
            await self._stream.write(data)
        else:
            await self._stream.eof()

    @classmethod
    @asynccontextmanager
    async def listen(cls, receive: HttpReceiveCallable):
        async with AsyncSpoolStream() as stream:
            stream = cls(stream)
            listen_task = asyncio.create_task(stream._listener(receive))
            try:
                yield stream
            finally:
                listen_task.cancel()
                with suppress(asyncio.CancelledError):
                    await listen_task


class StreamReceiveBytes(_StreamReceiveBase):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[bytes] = []
        self._data = None
        self._finished = asyncio.Event()

    @override
    async def _receive(self) -> bytes | None:
        await self._finished.wait()
        if not self._data:
            return None
        result = self._data
        self._data = None
        return result

    @override
    async def _send(self, data: bytes | None) -> None:
        if data:
            self._chunks.append(data)
        else:
            self._data = b"".join(self._chunks)
            self._finished.set()


class StreamReceiveDirect(_StreamReceiveBase):
    def __init__(self) -> None:
        super().__init__()
        self._data = None
        self._condition = asyncio.Condition()
        self._finished = False

    @override
    async def _receive(self) -> bytes | None:
        async with self._condition:
            await self._condition.wait_for(self._readable)
            if self._data is None:
                return None
            to_return = self._data
            self._data = None
            self._condition.notify_all()
        return to_return

    @override
    async def _send(self, data: bytes | None) -> None:
        async with self._condition:
            await self._condition.wait_for(self._writable)
            self._data = data
            if data is None:
                self._finished = True
            self._condition.notify_all()

    def _readable(self) -> bool:
        return self._data is not None or self._finished

    def _writable(self) -> bool:
        return not self._finished and self._data is None
