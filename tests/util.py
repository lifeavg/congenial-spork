from src.asgi_types import AsgiApp, HttpMiddleware, Receive, Scope, Send


class TestHandler:
    def __init__(self) -> None:
        self.stack = []

    async def __call__(
        self, scope: Scope | None = None, receive: Receive | None = None, send: Send | None = None
    ) -> None:
        if not scope:
            self.stack.append("r")
        else:
            self.stack.append(scope)
        return " ".join([str(i) for i in self.stack])


class TestMiddleware:
    def __init__(self, handler: TestHandler, name: str = "mdv") -> None:
        self.handler = handler
        self.stack = handler.stack
        self.name = name

    async def __call__(
        self, scope: Scope | None = None, receive: Receive | None = None, send: Send | None = None
    ) -> None:
        self.stack.append(self.name)
        await self.handler(scope, receive, send)
        self.stack.append(self.name)
        return " ".join([str(i) for i in self.stack])


def handler_factory() -> AsgiApp:
    return TestHandler()


def middleware_factory(name: str) -> HttpMiddleware:
    return lambda x: TestMiddleware(x, name)
