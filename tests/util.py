from collections.abc import Callable, Hashable
from typing import override

from src.router import ConnectionProtocolType, Router


class TestRouter[T, W](Router):
    @override
    def lookup(  # type: ignore
        self, path: str, protocol: ConnectionProtocolType, method: Hashable = None
    ) -> tuple[T | None, W | None, dict[str, str]]:  # type: ignore
        http, ws, mv, p = super().lookup(path, protocol, method)
        if http is not None:
            return mv(http), ws, p
        return http, ws, p


type Handler = Callable[[str], str]
type Middleware = Callable[[Handler], Handler]


def handler(s: str) -> str:
    return s


def middleware(handler: Handler, name: str) -> Handler:
    def wrapped(s: str) -> str:
        return f"{name} {handler(s)} {name}"

    return wrapped


def handler_factory():
    return handler


def middleware_factory(name: str) -> Middleware:
    def wrapped(handler: Handler) -> Handler:
        return middleware(handler, name)

    return wrapped


def new_router():
    return TestRouter[Handler, Handler]()
