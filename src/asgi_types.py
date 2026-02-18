from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any, Literal, NotRequired, Optional, TypedDict

ScopeType = Literal["lifespan", "http", "websocket"]

EventType = Literal[
    "lifespan.startup",
    "lifespan.startup.complete",
    "lifespan.startup.failed",
    "lifespan.shutdown",
    "http.request",
    "http.response.start",
    "http.response.body",
    "http.disconnect",
    "http.response.trailers",
    "websocket.connect",
    "websocket.accept",
    "websocket.send",
    "websocket.receive",
    "websocket.disconnect",
]
HttpVersion = Literal["1.0", "1.1", "2"]
HttpMethod = Literal["GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE", "POST", "PATCH", "CONNECT"]
HttpScheme = Literal["http", "https"]
HttpHeaders = Iterable[Sequence[bytes]]


class AsgiInfo(TypedDict):
    version: str
    spec_version: NotRequired[str]


class HttpScope(TypedDict):
    type: Literal["http"]
    asgi: NotRequired[AsgiInfo]
    extensions: NotRequired[dict[str, dict]]
    http_version: HttpVersion
    method: HttpMethod
    scheme: HttpScheme
    path: str
    raw_path: NotRequired[bytes]
    query_string: bytes
    root_path: NotRequired[str]
    headers: HttpHeaders
    client: NotRequired[Iterable[str | int]]
    server: NotRequired[Iterable[str | Optional[int]]]
    state: NotRequired[dict[str, Any]]


WebsocketHttpVersion = Literal["1.1", "2"]
WebsocketScheme = Literal["ws", "wss"]


class WebsocketScope(TypedDict):
    type: Literal["websocket"]
    asgi: NotRequired[AsgiInfo]
    extensions: NotRequired[dict[str, dict]]
    http_version: WebsocketHttpVersion
    scheme: WebsocketScheme
    path: str
    raw_path: NotRequired[bytes]
    query_string: bytes
    root_path: NotRequired[str]
    headers: HttpHeaders
    client: NotRequired[Iterable[str | int]]
    server: NotRequired[Iterable[str | Optional[int]]]
    subprotocols: NotRequired[Iterable[str]]
    state: NotRequired[dict[str, Any]]


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: NotRequired[AsgiInfo]
    state: NotRequired[dict[str, Any]]


class HttpRequest(TypedDict):
    # receive
    type: Literal["http.request"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class HttpResponseStart(TypedDict):
    # send
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[HttpHeaders]
    trailers: NotRequired[bool]


class HttpResponseBody(TypedDict):
    # send
    type: Literal["http.response.body"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class HttpDisconnect(TypedDict):
    # receive
    type: Literal["http.disconnect"]


class WebsocketConnect(TypedDict):
    # receive
    type: Literal["websocket.connect"]


class WebsocketAccept(TypedDict):
    # send
    type: Literal["websocket.accept"]
    subprotocol: NotRequired[str]
    headers: NotRequired[HttpHeaders]


class WebsocketReceive(TypedDict):
    # receive
    type: Literal["websocket.receive"]
    bytes: NotRequired[bytes]
    text: NotRequired[str]


class WebsocketSend(TypedDict):
    # send
    type: Literal["websocket.send"]
    bytes: NotRequired[bytes]
    text: NotRequired[str]


class WebsocketDisconnect(TypedDict):
    # receive
    type: Literal["websocket.disconnect"]
    code: int
    reason: NotRequired[str]


class WebsocketClose(TypedDict):
    # send
    type: Literal["websocket.close"]
    code: NotRequired[int]
    reason: NotRequired[str]


class LifespanStartup(TypedDict):
    # receive
    type: Literal["lifespan.startup"]


class LifespanStartupComplete(TypedDict):
    # send
    type: Literal["lifespan.startup.complete"]


class LifespanStartupFailed(TypedDict):
    # send
    type: Literal["lifespan.startup.failed"]
    message: NotRequired[str]


class LifespanShutdown(TypedDict):
    # receive
    type: Literal["lifespan.shutdown"]


class LifespanShutdownComplete(TypedDict):
    # send
    type: Literal["lifespan.shutdown.complete"]


class LifespanShutdownFailed(TypedDict):
    # send
    type: Literal["lifespan.shutdown.failed"]
    message: NotRequired[str]


type HttpReceiveEvent = HttpRequest | HttpDisconnect
WebsocketReceiveEvent = WebsocketConnect | WebsocketReceive | WebsocketDisconnect
LifespanReceiveEvent = LifespanStartup | LifespanShutdown

HttpSendEvent = HttpResponseStart | HttpResponseBody
WebsocketSendEvent = WebsocketAccept | WebsocketSend | WebsocketClose
LifespanSendEvent = LifespanStartupComplete | LifespanStartupFailed | LifespanShutdownComplete | LifespanShutdownFailed

type HttpReceiveCallable = Callable[[], Awaitable[HttpReceiveEvent]]
WebsocketReceiveCallable = Callable[[], Awaitable[WebsocketReceiveEvent]]
LifespanReceiveCallable = Callable[[], Awaitable[LifespanSendEvent]]

type HttpSendCallable = Callable[[HttpSendEvent], Awaitable[None]]
WebsocketSendCallable = Callable[[WebsocketSendEvent], Awaitable[None]]
LifespanSendCallable = Callable[[LifespanSendEvent], Awaitable[None]]

Scope = HttpScope | WebsocketScope | LifespanScope
Receive = HttpReceiveCallable | WebsocketReceiveCallable | LifespanReceiveCallable
Send = HttpSendCallable | WebsocketSendCallable | LifespanSendCallable

HttpHandler = Callable[[HttpScope, HttpReceiveCallable, HttpSendCallable], Awaitable[None]]
WebsocketHandler = Callable[[WebsocketScope, WebsocketReceiveCallable, WebsocketSendCallable], Awaitable[None]]
LifespanHandler = Callable[[LifespanScope, LifespanReceiveCallable, LifespanSendCallable], Awaitable[None]]

AsgiApp = Callable[[Scope, Receive, Send], Awaitable[None]]

HttpMiddleware = Callable[[HttpHandler], HttpHandler]
