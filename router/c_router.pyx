# cython: language_level=3
# cython: boundscheck=False, wraparound=False, nonecheck=False
_UNSET = object()


cdef class Node:
    cdef dict static
    cdef Node param
    cdef str param_name
    cdef Node wildcard
    cdef str wildcard_name
    cdef object handler

    def __cinit__(self):
        self.static = {}
        self.param = None
        self.param_name = None
        self.wildcard = None
        self.wildcard_name = None
        self.handler = None


cdef inline Node empty_node():
    return Node()


cdef class RadixRouter:
    cdef Node root

    def __cinit__(self):
        self.root = empty_node()

    def add(self, str path, object handler):
        if not path:
            raise ValueError("Empty path")

        if path == "/":
            if self.root.handler is not None:
                raise ValueError("Duplicate route: /")
            self.root.handler = handler
            return

        cdef list segments = self._split(path)
        cdef Node node = self.root
        cdef bint wildcard_seen = False
        cdef str seg, name
        cdef int i

        for i in range(len(segments)):
            seg = segments[i]

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
                elif node.wildcard_name != name:
                    raise ValueError("Conflicting wildcard names")

                node = node.wildcard
                break

            elif seg.startswith(":"):
                name = seg[1:]
                if node.param is None:
                    node.param = empty_node()
                    node.param_name = name
                elif node.param_name != name:
                    raise ValueError(
                        f"Conflicting param names at same position: "
                        f"{node.param_name} vs {name}"
                    )
                node = node.param

            else:
                if seg not in node.static:
                    node.static[seg] = empty_node()
                node = node.static[seg]

        if node.handler is not None:
            raise ValueError(f"Duplicate route: {path}")

        node.handler = handler

    def lookup(self, str path):
        if not path or path == "/":
            return self.root.handler, {}

        cdef list segments = self._split(path)
        cdef dict params = {}
        cdef list undo_stack = []

        # stack entries:
        # (node, index, undo_len, pending_key, pending_value)
        cdef list stack = [(self.root, 0, 0, None, None)]

        cdef Node node, nxt
        cdef int i, undo_len
        cdef str pending_key, seg
        cdef object pending_value, old
        cdef str rb_key
        cdef object rb_old

        while stack:
            node, i, undo_len, pending_key, pending_value = stack.pop()

            # rollback (IMPORTANT: do NOT overwrite pending_key)
            while len(undo_stack) > undo_len:
                rb_key, rb_old = undo_stack.pop()
                if rb_old is _UNSET:
                    del params[rb_key]
                else:
                    params[rb_key] = rb_old

            # apply pending mutation
            if pending_key is not None:
                if pending_key in params:
                    old = params[pending_key]
                    undo_stack.append((pending_key, old))
                else:
                    undo_stack.append((pending_key, _UNSET))
                params[pending_key] = pending_value

            # end of path
            if i == len(segments):
                if node.handler is not None:
                    return node.handler, dict(params)

                if node.wildcard is not None:
                    stack.append(
                        (node.wildcard, len(segments), len(undo_stack),
                        node.wildcard_name, "")
                    )
                continue

            seg = segments[i]

            # wildcard (lowest priority)
            if node.wildcard is not None:
                stack.append(
                    (node.wildcard, len(segments), len(undo_stack),
                    node.wildcard_name, "/".join(segments[i:]))
                )

            # param
            if node.param is not None:
                stack.append(
                    (node.param, i + 1, len(undo_stack),
                    node.param_name, seg)
                )

            # static (highest priority)
            nxt = node.static.get(seg)
            if nxt is not None:
                stack.append((nxt, i + 1, len(undo_stack), None, None))

        return None, {}

    cpdef list _split(self, str path):
        return [seg for seg in path.strip("/").split("/") if seg]
