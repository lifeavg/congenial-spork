from .asgi_types import HttpReceiveCallable, HttpScope, HttpSendCallable
from .response import Response
from .stream_receive import StreamReceive


class HttpConnection:
    def __init__(self, request_streamer: type[StreamReceive], response_streamer: type[Response]) -> None:
        self._request_streamer = request_streamer
        self._response_streamer = response_streamer

    async def __call__(self, scope: HttpScope, receive: HttpReceiveCallable, send: HttpSendCallable) -> None:
        async with self._request_streamer.listen(receive) as stream:
            async with self._response_streamer.start(send, stream.is_connected) as resp:
                chunks: list[bytes] = []
                async for chunk in stream:
                    chunks.append(chunk)
                body = b"".join(chunks)
                await resp.body("Echo: ".encode() + body)
