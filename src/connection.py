from .asgi_types import HttpReceiveCallable, HttpScope, HttpSendCallable
from .response import response
from .stream_receive import StreamReceive


class HttpConnection:
    def __init__(self, input_streamer: type[StreamReceive]) -> None:
        self._input_streamer = input_streamer

    async def __call__(self, scope: HttpScope, receive: HttpReceiveCallable, send: HttpSendCallable) -> None:
        async with self._input_streamer.listen(receive) as stream:
            chunks: list[bytes] = []
            async for chunk in stream:
                chunks.append(chunk)
            body = b"".join(chunks)
            async with response(send, stream.is_connected) as resp:
                await resp.body("Echo: ".encode() + body)
