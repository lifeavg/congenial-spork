from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from itertools import chain
from typing import Literal, Optional, Self, cast

from .util import chain_decorators

type HttpHandlerMap[Y: Hashable, T] = dict[Y, T]
type ConnectionProtocolType = Literal["http", "ws"]


@dataclass(slots=True)
class Node[T, W]:
    static: dict[str, "Node[T, W]"] = cast(dict[str, "Node[T, W]"], field(default_factory=dict))
    param: Optional["Node[T, W]"] = None
    param_name: Optional[str] = None
    wildcard: Optional["Node[T, W]"] = None
    wildcard_name: Optional[str] = None
    http: HttpHandlerMap[Hashable, T] = cast(HttpHandlerMap[Hashable, T], field(default_factory=dict))
    websocket: Optional[W] = None
    middleware: list[Callable[[T], T]] = cast(list[Callable[[T], T]], field(default_factory=list))


def _split(path: str) -> list[str]:
    return [seg for seg in path.strip("/").split("/") if seg]


def _merge_nodes[T, W](target: Node[T, W], source: Node[T, W]) -> None:
    """
    Recursively merge a source node into a target node.
    """
    # Merge HTTP handlers
    target_handlers = {k for k, v in target.http.items() if v is not None}
    source_handlers = {k for k, v in source.http.items() if v is not None}
    handlers_intersection = target_handlers.intersection(source_handlers)
    if handlers_intersection:
        raise ValueError(
            f"Mount conflict: Multiple HTTP handlers for same path: {' '.join([str(i) for i in handlers_intersection])}"
        )
    target.http.update(source.http)

    # Append HTTP middleware (preserving order)
    target.middleware.extend(source.middleware)

    # Set WebSocket handler if not already set
    if source.websocket is not None:
        if target.websocket is not None:
            raise ValueError("Mount conflict: Multiple websocket handlers for same path")
        target.websocket = source.websocket

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


class Router[T, W]:
    def __init__(self) -> None:
        self.root = Node[T, W]()

    def add(
        self,
        path: str,
        http_method: Hashable = None,
        http_handler: T | None = None,
        middleware: Callable[[T], T] | None = None,
        ws_handler: W | None = None,
    ) -> None:
        if not path:
            raise ValueError("Empty path")

        if path == "/":
            if http_handler is not None and self.root.http.get(http_method) is not None:
                raise ValueError("Duplicate http route: /")
            if ws_handler is not None and self.root.websocket is not None:
                raise ValueError("Duplicate websocket route: /")
            if http_handler is not None:
                self.root.http[http_method] = http_handler
            if ws_handler is not None:
                self.root.websocket = ws_handler
            if middleware is not None:
                self.root.middleware.append(middleware)
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

        if http_handler is not None and node.http.get(http_method) is not None:
            raise ValueError(f"Duplicate http route: {path}")
        if ws_handler is not None and node.websocket is not None:
            raise ValueError(f"Duplicate websocket route: {path}")
        if http_handler is not None:
            node.http[http_method] = http_handler
        if ws_handler is not None:
            node.websocket = ws_handler
        if middleware is not None:
            node.middleware.append(middleware)

    def mount(self, at: str, other: Self) -> None:
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
            self.root.http.update(other.root.http)
            self.root.middleware.extend(other.root.middleware)
            if other.root.websocket is not None:
                if self.root.websocket is not None:
                    raise ValueError(f"Mount conflict: Both routers have websocket handlers at path {at}")
                self.root.websocket = other.root.websocket

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
            current_node.http.update(other.root.http)
            current_node.middleware.extend(other.root.middleware)
            if other.root.websocket is not None:
                if current_node.websocket is not None:
                    raise ValueError(f"Mount conflict: Both routers have websocket handlers at path {at}")
                current_node.websocket = other.root.websocket

    def lookup(
        self, path: str, protocol: ConnectionProtocolType, method: Hashable = None
    ) -> tuple[Optional[T], Optional[W], Callable[[T], T], dict[str, str]]:
        if not path or path == "/":
            if protocol == "http":
                return self.root.http.get(method), None, chain_decorators(self.root.middleware), {}
            if protocol == "ws":
                return None, self.root.websocket, chain_decorators(self.root.middleware), {}
        segments = _split(path)
        mdw_stack: list[list[Callable[[T], T]]] = []
        params_stack: list[tuple[str | None, str | None]] = []

        # stack entries:
        # (node, index, undo_len, pending_key, pending_value)
        stack: list[tuple[Node[T, W], int, int, str | None, str | None]] = [(self.root, 0, 0, None, None)]

        while stack:
            node, i, undo_len, pending_key, pending_value = stack.pop()
            # rollback (IMPORTANT: do NOT overwrite pending_key)
            if len(params_stack) > undo_len:
                params_stack = params_stack[:undo_len]
                mdw_stack = mdw_stack[:undo_len]

            # apply pending mutation
            params_stack.append((pending_key, pending_value))
            mdw_stack.append(node.middleware if protocol == "http" else [])
            undo_len += 1

            # end of path
            if i == len(segments):
                if protocol == "http":
                    handler = node.http.get(method)
                    if handler is not None:
                        params = dict(params_stack)
                        if None in params:
                            del params[None]
                        return (
                            handler,
                            None,
                            chain_decorators(chain(*reversed(mdw_stack))),
                            cast(dict[str, str], params),
                        )
                elif protocol == "ws":
                    if node.websocket is not None:
                        params = dict(params_stack)
                        if None in params:
                            del params[None]
                        return (
                            None,
                            node.websocket,
                            chain_decorators(chain(*reversed(mdw_stack))),
                            cast(dict[str, str], params),
                        )
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

        return None, None, lambda x: x, {}
