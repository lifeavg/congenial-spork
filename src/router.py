from dataclasses import dataclass, field
from itertools import chain
from typing import Literal, Optional

from .asgi_types import HttpHandler, HttpMethod, HttpMiddleware, WebsocketHandler

HttpHandlerMap = dict[HttpMethod, HttpHandler]
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


def _split(path: str) -> list[str]:
    return [seg for seg in path.strip("/").split("/") if seg]


def _merge_nodes(target: Node, source: Node) -> None:
    """
    Recursively merge a source node into a target node.
    """
    # Merge HTTP handlers
    target_handlers = {k for k, v in target.http.handlers.items() if v is not None}
    source_handlers = {k for k, v in source.http.handlers.items() if v is not None}
    handlers_intersection = target_handlers.intersection(source_handlers)
    if handlers_intersection:
        raise ValueError(f"Mount conflict: Multiple HTTP handlers for same path: {' '.join(handlers_intersection)}")
    target.http.handlers.update(source.http.handlers)

    # Append HTTP middleware (preserving order)
    target.http.middleware.extend(source.http.middleware)

    # Set WebSocket handler if not already set
    if source.websocket.handler is not None:
        if target.websocket.handler is not None:
            raise ValueError("Mount conflict: Multiple websocket handlers for same path")
        target.websocket.handler = source.websocket.handler

    # Recursively merge static children
    for key, source_child in source.static.items():
        if key in target.static:
            _merge_nodes(target.static[key], source_child)
        else:
            target.static[key] = source_child

    # Merge param node
    if source.param is not None:
        if target.param is not None:
            # Check param name compatibility
            if target.param_name != source.param_name:
                raise ValueError(f"Mount conflict: Param name mismatch '{target.param_name}' vs '{source.param_name}'")
            _merge_nodes(target.param, source.param)
        else:
            target.param = source.param
            target.param_name = source.param_name

    # Merge wildcard node
    if source.wildcard is not None:
        if target.wildcard is not None:
            # Check wildcard name compatibility
            if target.wildcard_name != source.wildcard_name:
                raise ValueError(
                    f"Mount conflict: Wildcard name mismatch '{target.wildcard_name}' vs '{source.wildcard_name}'"
                )
            _merge_nodes(target.wildcard, source.wildcard)
        else:
            target.wildcard = source.wildcard
            target.wildcard_name = source.wildcard_name


class Router:
    def __init__(self) -> None:
        self.root = Node()

    def add(
        self,
        path: str,
        http_method: Optional[HttpMethod] = None,
        http_handler: Optional[HttpHandler] = None,
        http_middleware: Optional[HttpMiddleware] = None,
        ws_handler: Optional[WebsocketHandler] = None,
    ) -> None:
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

        segments = _split(path)
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

    def mount(self, at: str, other: Router) -> None:
        """
        Mount another router at a specific path prefix.

        Args:
            at: The path prefix where to mount the other router (e.g., "/api/v1")
            other: Another Router instance to mount
        """
        if not at or at == "/":
            # If mounting at root, merge all nodes from other router's root
            # Handle static children
            for key, child_node in other.root.static.items():
                if key in self.root.static:
                    # Merge into existing node
                    _merge_nodes(self.root.static[key], child_node)
                else:
                    # Add new node
                    self.root.static[key] = child_node

            # Handle param node
            if other.root.param is not None:
                if self.root.param is not None:
                    _merge_nodes(self.root.param, other.root.param)
                else:
                    self.root.param = other.root.param
                    self.root.param_name = other.root.param_name

            # Handle wildcard node
            if other.root.wildcard is not None:
                if self.root.wildcard is not None:
                    _merge_nodes(self.root.wildcard, other.root.wildcard)
                else:
                    self.root.wildcard = other.root.wildcard
                    self.root.wildcard_name = other.root.wildcard_name

            # Merge root-level handlers and middleware
            self.root.http.handlers.update(other.root.http.handlers)
            self.root.http.middleware.extend(other.root.http.middleware)
            if other.root.websocket.handler is not None:
                if self.root.websocket.handler is not None:
                    raise ValueError(f"Mount conflict: Both routers have websocket handlers at path {at}")
                self.root.websocket.handler = other.root.websocket.handler

        else:
            # Parse the mount path into segments
            segments = _split(at)

            # Navigate to the mount point
            current_node = self.root
            for seg in segments:
                if seg.startswith("*"):
                    raise ValueError(f"Cannot mount under wildcard path: {at}")

                if seg.startswith(":"):
                    # Create parameter node if it doesn't exist
                    if current_node.param is None:
                        current_node.param = Node()
                        current_node.param_name = seg[1:]
                    current_node = current_node.param
                else:
                    # Create static node if it doesn't exist
                    if seg not in current_node.static:
                        current_node.static[seg] = Node()
                    current_node = current_node.static[seg]

            # Now current_node is the mount point - merge other's root into it
            # Handle static children
            for key, child_node in other.root.static.items():
                if key in current_node.static:
                    # Merge into existing node
                    _merge_nodes(current_node.static[key], child_node)
                else:
                    # Add new node
                    current_node.static[key] = child_node

            # Handle param node
            if other.root.param is not None:
                if current_node.param is not None:
                    _merge_nodes(current_node.param, other.root.param)
                else:
                    current_node.param = other.root.param
                    current_node.param_name = other.root.param_name

            # Handle wildcard node
            if other.root.wildcard is not None:
                if current_node.wildcard is not None:
                    _merge_nodes(current_node.wildcard, other.root.wildcard)
                else:
                    current_node.wildcard = other.root.wildcard
                    current_node.wildcard_name = other.root.wildcard_name

            # Merge root-level handlers and middleware from other router
            current_node.http.handlers.update(other.root.http.handlers)
            current_node.http.middleware.extend(other.root.http.middleware)
            if other.root.websocket.handler is not None:
                if current_node.websocket.handler is not None:
                    raise ValueError(f"Mount conflict: Both routers have websocket handlers at path {at}")
                current_node.websocket.handler = other.root.websocket.handler

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
        segments = _split(path)
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
