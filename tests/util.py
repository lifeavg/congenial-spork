from src.asgi_types import AsgiApp, HttpMiddleware, Receive, Scope, Send


class Connection:
    def __init__(self) -> None:
        self.data = ""

    async def receive(self):
        return ""

    async def send(self, dt):
        self.data += dt


class TestHandler:
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        dt = await receive()
        await send(dt + " r")


class TestMiddleware:
    def __init__(self, handler: TestHandler, name: str = "mdv") -> None:
        self.handler = handler
        self.name = name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:

        async def _receive():
            dt = await receive()
            if dt:
                return str(await receive()) + " " + self.name
            else:
                return self.name

        await self.handler(scope, _receive, send)
        await send(" " + self.name)


def handler_factory() -> AsgiApp:
    return TestHandler()


def middleware_factory(name: str) -> HttpMiddleware:
    return lambda x: TestMiddleware(x, name)
