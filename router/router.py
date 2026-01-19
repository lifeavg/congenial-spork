from dataclasses import dataclass
from typing import Any, Optional

_UNSET = object()


@dataclass(slots=True)
class Node:
    static: dict[str, "Node"]
    param: Optional["Node"]
    param_name: Optional[str]
    wildcard: Optional["Node"]
    wildcard_name: Optional[str]
    handler: Any


def empty_node() -> Node:
    return Node(
        static={},
        param=None,
        param_name=None,
        wildcard=None,
        wildcard_name=None,
        handler=None,
    )


class RadixRouter:
    def __init__(self):
        self.root = empty_node()

    def add(self, path: str, handler: Any):
        if path == "":
            raise ValueError("Empty path")

        if path == "/":
            if self.root.handler is not None:
                raise ValueError("Duplicate route: /")
            self.root.handler = handler
            return

        segments = self._split(path)
        node = self.root
        wildcard_seen = False

        for i, seg in enumerate(segments):
            if "*" in seg and not seg.startswith("*"):
                raise ValueError(f"Invalid wildcard pattern: {seg}")
            if seg.startswith("*"):
                if wildcard_seen:
                    raise ValueError("Multiple wildcards")
                if i != len(segments) - 1:
                    raise ValueError("Wildcard must be last")
                if len(seg) == 1:
                    raise ValueError("Unnamed wildcard")

                wildcard_seen = True
                name = seg[1:]

                if node.wildcard is None:
                    node.wildcard = empty_node()
                    node.wildcard_name = name
                node = node.wildcard
                break
            elif seg.startswith(":"):
                name = seg[1:]
                if node.param is None:
                    node.param = empty_node()
                    node.param_name = name
                else:
                    if node.param_name != name:
                        raise ValueError(f"Conflicting param names at same position: {node.param_name} vs {name}")
                node = node.param
            else:
                if seg not in node.static:
                    node.static[seg] = empty_node()
                node = node.static[seg]

        if node.handler is not None:
            raise ValueError(f"Duplicate route: {path}")

        node.handler = handler

    def lookup(self, path: str) -> tuple[Any, dict[str, str]]:
        if path == "" or path == "/":
            return self.root.handler, {}

        segments = self._split(path)
        params: dict[str, str] = {}

        # stack entries:
        # (node, index, undo_len, pending_key, pending_value)
        stack = [(self.root, 0, 0, None, None)]
        undo_stack: list[tuple[str, object]] = []

        while stack:
            node, i, undo_len, key, value = stack.pop()

            # rollback
            while len(undo_stack) > undo_len:
                k, old = undo_stack.pop()
                if old is _UNSET:
                    del params[k]
                else:
                    params[k] = old

            # apply pending mutation
            if key is not None:
                old = params.get(key, _UNSET)
                undo_stack.append((key, old))
                params[key] = value

            # end of path
            if i == len(segments):
                if node.handler is not None:
                    return node.handler, dict(params)

                if node.wildcard is not None:
                    name = node.wildcard_name
                    stack.append((node.wildcard, len(segments), len(undo_stack), name, ""))
                continue

            seg = segments[i]

            # 3 wildcard (lowest priority)
            if node.wildcard is not None:
                name = node.wildcard_name
                stack.append((node.wildcard, len(segments), len(undo_stack), name, "/".join(segments[i:])))

            # 2 param
            if node.param is not None:
                name = node.param_name
                stack.append((node.param, i + 1, len(undo_stack), name, seg))

            # 1 static (highest priority)
            nxt = node.static.get(seg)
            if nxt is not None:
                stack.append((nxt, i + 1, len(undo_stack), None, None))

        return None, {}

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
