from functools import partial

from src.asgi_types import AsgiApp, HttpHandler, HttpMiddleware, Receive, Scope, Send


class Connection:
    def __init__(self) -> None:
        self.data = ""

    async def receive(self):
        return ""

    async def send(self, dt):
        self.data += dt


async def handler(scope: Scope, receive: Receive, send: Send) -> None:
    dt = await receive()
    await send(dt + " r")


async def middleware(handler: HttpHandler, name: str, scope: Scope, receive: Receive, send: Send) -> None:

    async def _receive():
        dt = await receive()
        if dt:
            return str(await receive()) + " " + name
        else:
            return name

    await handler(scope, _receive, send)
    await send(" " + name)


def handler_factory() -> AsgiApp:
    return handler


def middleware_factory(name: str) -> HttpMiddleware:
    return lambda x: partial(middleware, x, name)
