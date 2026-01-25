from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from itertools import chain
from typing import Literal, Optional

HttpMethod = Literal["GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE", "POST", "PATCH", "CONNECT", "__ANY__"]
HttpRequest = type(object)
WebsocketRequest = type(object)
Response = type(object)
HttpHandler = Callable[[HttpRequest], Awaitable[Response]]
HttpMiddleware = Callable[[HttpHandler], HttpHandler]
HttpHandlerMap = dict[HttpMethod, HttpHandler]
WebsocketHandler = Callable[[WebsocketRequest], Awaitable[None]]
ConnectionProtocolType = Literal["http", "ws"]


@dataclass(slots=True)
class Http:
    handlers: HttpHandlerMap = field(default_factory=dict)
    middleware: list[HttpMiddleware] = field(default_factory=list)


@dataclass(slots=True)
class Websocket:
    handler: Optional[WebsocketHandler] = None


@dataclass(slots=True)
class Node:
    static: dict[str, "Node"] = field(default_factory=dict)
    param: Optional["Node"] = None
    param_name: Optional[str] = None
    wildcard: Optional["Node"] = None
    wildcard_name: Optional[str] = None
    http: Http = field(default_factory=Http)
    websocket: Websocket = field(default_factory=Websocket)


class Router:
    def __init__(self):
        self.root = Node()

    def add(
        self,
        path: str,
        http_method: Optional[HttpMethod] = None,
        http_handler: Optional[HttpHandler] = None,
        http_middleware: Optional[HttpMiddleware] = None,
        ws_handler: Optional[WebsocketHandler] = None,
    ):
        if not path:
            raise ValueError("Empty path")
        if http_method is None:
            http_method = "__ANY__"

        if path == "/":
            if http_handler is not None and self.root.http.handlers.get(http_method) is not None:
                raise ValueError("Duplicate http route: /")
            if ws_handler is not None and self.root.websocket.handler is not None:
                raise ValueError("Duplicate websocket route: /")
            if http_handler is not None:
                self.root.http.handlers[http_method] = http_handler
            if ws_handler is not None:
                self.root.websocket.handler = ws_handler
            if http_middleware is not None:
                self.root.http.middleware.append(http_middleware)
            return

        segments = self._split(path)
        node = self.root
        wildcard_seen = False

        for i, seg in enumerate(segments):
            if "*" in seg and not seg.startswith("*"):
                raise ValueError(f"Invalid wildcard pattern: {seg} in {path}")
            if seg.startswith("*"):
                if wildcard_seen:
                    raise ValueError(f"Multiple wildcards: {path}")
                if i != len(segments) - 1:
                    raise ValueError(f"Wildcard must be last: {path}")
                if len(seg) == 1:
                    raise ValueError(f"Unnamed wildcard: {path}")

                wildcard_seen = True
                name = seg[1:]

                if node.wildcard is None:
                    node.wildcard = Node()
                    node.wildcard_name = name
                elif node.wildcard_name != name:
                    raise ValueError(f"Conflicting wildcard names: {path}")
                node = node.wildcard
                break
            elif seg.startswith(":"):
                name = seg[1:]
                if node.param is None:
                    node.param = Node()
                    node.param_name = name
                elif node.param_name != name:
                    raise ValueError(f"Conflicting param names at same position: {node.param_name} vs {name} in {path}")
                node = node.param
            else:
                if seg not in node.static:
                    node.static[seg] = Node()
                node = node.static[seg]

        if http_handler is not None and node.http.handlers.get(http_method) is not None:
            raise ValueError(f"Duplicate http route: {path}")
        if ws_handler is not None and node.websocket.handler is not None:
            raise ValueError(f"Duplicate websocket route: {path}")
        if http_handler is not None:
            node.http.handlers[http_method] = http_handler
        if ws_handler is not None:
            node.websocket.handler = ws_handler
        if http_middleware is not None:
            node.http.middleware.append(http_middleware)

    def lookup(
        self, path: str, protocol: ConnectionProtocolType, method: Optional[HttpMethod] = None
    ) -> tuple[Optional[HttpHandler], Optional[WebsocketHandler], dict[str, str]]:
        if method is None:
            method = "__ANY__"
        if not path or path == "/":
            if protocol == "http":
                handler = self.root.http.handlers.get(method)
                if handler is not None:
                    for mv in self.root.http.middleware:
                        handler = mv(handler)
                return handler, None, {}
            if protocol == "ws":
                return None, self.root.websocket.handler, {}
        segments = self._split(path)
        mdw_stack = []
        params_stack: list[tuple[str | None, str | None]] = []

        # stack entries:
        # (node, index, undo_len, pending_key, pending_value)
        stack = [(self.root, 0, 0, None, None)]

        while stack:
            node, i, undo_len, pending_key, pending_value = stack.pop()
            # rollback (IMPORTANT: do NOT overwrite pending_key)
            if len(params_stack) > undo_len:
                params_stack = params_stack[:undo_len]
                mdw_stack = mdw_stack[:undo_len]

            # apply pending mutation
            params_stack.append((pending_key, pending_value))
            mdw_stack.append(node.http.middleware if protocol == "http" else [])
            undo_len += 1

            # end of path
            if i == len(segments):
                if protocol == "http":
                    handler = node.http.handlers.get(method)
                    if handler is not None:
                        for mv in chain(*reversed(mdw_stack)):
                            handler = mv(handler)
                        params = dict(params_stack)
                        if None in params:
                            del params[None]
                        return handler, None, params
                elif protocol == "ws":
                    if node.websocket.handler is not None:
                        params = dict(params_stack)
                        if None in params:
                            del params[None]
                        return None, node.websocket.handler, params
                if node.wildcard is not None:
                    stack.append((node.wildcard, len(segments), undo_len, node.wildcard_name, ""))
                continue

            seg = segments[i]

            # wildcard (lowest priority)
            if node.wildcard is not None:
                stack.append((node.wildcard, len(segments), undo_len, node.wildcard_name, "/".join(segments[i:])))
            # param
            if node.param is not None:
                stack.append((node.param, i + 1, undo_len, node.param_name, seg))
            # static (highest priority)
            nxt = node.static.get(seg)
            if nxt is not None:
                stack.append((nxt, i + 1, undo_len, None, None))

        return None, None, {}

    def print_tree(self):
        def walk(n: Node, prefix: str):
            if n.handler is not None:
                print(f"{prefix} [HANDLER]")

            for k, v in n.static.items():
                print(f"{prefix}/{k}")
                walk(v, prefix + "/" + k)

            if n.param:
                print(f"{prefix}/:{n.param_name}")
                walk(n.param, prefix + "/:" + str(n.param_name))

            if n.wildcard:
                print(f"{prefix}/*{n.wildcard_name}")
                walk(n.wildcard, prefix + "/*" + str(n.wildcard_name))

        walk(self.root, "")

    @staticmethod
    def _split(path: str) -> list[str]:
        return [seg for seg in path.strip("/").split("/") if seg]
