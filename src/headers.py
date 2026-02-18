from collections import defaultdict
from collections.abc import Generator, Iterable, Mapping, Sequence
from functools import singledispatchmethod
from typing import Any, Self

# === Precomputed tables (built once at import) ===

# Allowed header name characters (token, lowercase only)
_ALLOWED_NAME = bytearray(256)
for c in b"!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyz":
    _ALLOWED_NAME[c] = 1

_ALLOWED_NAME = bytes(_ALLOWED_NAME)

# Allowed header value characters
# HTAB (0x09), SP (0x20–0x7E except DEL), and obs-text (0x80–0xFF)
_ALLOWED_VALUE = bytearray(256)

for i in range(256):
    if i == 0x09:  # HTAB
        _ALLOWED_VALUE[i] = 1
    elif 0x20 <= i <= 0x7E and i != 0x7F:  # visible ASCII except DEL
        _ALLOWED_VALUE[i] = 1
    elif 0x80 <= i <= 0xFF:  # obs-text allowed in HTTP/1.1
        _ALLOWED_VALUE[i] = 1

_ALLOWED_VALUE = bytes(_ALLOWED_VALUE)


def _validated_key(k: bytes) -> bytes:
    """
    Safe for HTTP/1.1, HTTP/2, HTTP/3.
    Enforces lowercase.
    """
    if not k:
        raise ValueError("Header name cannot be empty")

    # Branchless validation via lookup table
    for c in k:
        if not _ALLOWED_NAME[c]:
            raise ValueError(f"Invalid character in header name: {k}")
    return k


def _validated_value(v: bytes) -> bytes:
    """
    Safe for HTTP/1.1, HTTP/2, HTTP/3.
    Rejects CR, LF, NUL, DEL, and other control chars except HTAB.
    """
    # Explicit CRLF fast check (very common attack vector)
    if b"\r" in v or b"\n" in v:
        raise ValueError(f"Header value must not contain CR or LF: {v}")
    # Branchless validation via lookup table
    for c in v:
        if not _ALLOWED_VALUE[c]:
            raise ValueError(f"Invalid character in header value: {v}")
    return v


class HeadersImmutable:
    encoding = "latin-1"

    def __init__(self) -> None:
        self._keys: list[bytes] = []
        self._values: list[bytes] = []

    def serialize(self) -> Iterable[tuple[bytes, bytes]]:
        return zip(self._keys, self._values)

    @classmethod
    def load(cls, other: Self | Mapping | Iterable) -> Self:
        return cls._load(*cls._parse(other))

    @classmethod
    def load_no_validation(cls, other: Iterable[Sequence[bytes]]) -> Self:
        keys: list[bytes] = []
        values: list[bytes] = []
        for i in other:
            keys.append(i[0])
            values.append(i[1])
        return cls._load(keys, values)

    def keys(self) -> Generator[str, None, None]:
        return (key.decode(self.encoding) for key in self._keys)

    def values(self) -> Generator[str, None, None]:
        return (value.decode(self.encoding) for value in self._values)

    def find(self, key: str | bytes) -> Generator[str, None, None]:
        searched_key = self._encode_key(key)
        return (self._values[id].decode(self.encoding) for id, key in enumerate(self._keys) if key == searched_key)

    def __contains__(self, key: str | bytes) -> bool:
        return self._encode_key(key) in self._keys

    def __len__(self) -> int:
        return len(self._keys)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HeadersImmutable):
            return False
        return self._keys == other._keys and self._values == other._values

    def __iter__(self) -> Generator[tuple[str, str], None, None]:
        return ((k.decode(self.encoding), v.decode(self.encoding)) for k, v in zip(self._keys, self._values))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            + ", ".join(
                f"'{k.decode(self.encoding, errors='replace')}: {v.decode(self.encoding)}'"
                for k, v in zip(self._keys, self._values)
            )
            + ")"
        )

    @classmethod
    def _load(cls, keys: Iterable[bytes], values: Iterable[bytes]) -> Self:
        instance = cls()
        instance._keys = list(keys)
        instance._values = list(values)
        return instance

    @classmethod
    def _encode_key(cls, val) -> bytes:
        if isinstance(val, bytes):
            return _validated_key(val.lower())
        if isinstance(val, str):
            val = val.lower()
        try:
            return _validated_key(val.encode(cls.encoding))
        except Exception as e:
            raise ValueError(f"Key {val} could not be encoded to {cls.encoding}") from e

    @classmethod
    def _encode_value(cls, val) -> bytes:
        if isinstance(val, bytes):
            return _validated_value(val)
        try:
            return _validated_value(val.encode(cls.encoding))
        except Exception as e:
            raise ValueError(f"Value {val} could not be encoded to {cls.encoding}") from e

    @singledispatchmethod
    @classmethod
    def _parse(cls, other: Iterable) -> tuple[list[bytes], list[bytes]]:
        keys: list[bytes] = []
        values: list[bytes] = []
        for i in other:
            li = tuple(i)
            keys.append(cls._encode_key(li[0]))
            values.append(cls._encode_value(li[1]))
        return keys, values

    @_parse.register
    @classmethod
    def _(cls, other: Mapping) -> tuple[list[bytes], list[bytes]]:
        return [cls._encode_key(i) for i in other.keys()], [cls._encode_value(i) for i in other.values()]


@HeadersImmutable._parse.register  # type: ignore
@classmethod
def _HeadersImmutable_parse(cls, other: HeadersImmutable) -> tuple[list[bytes], list[bytes]]:
    return other._keys, other._values


class HeadersMutable(HeadersImmutable):
    def append(self, key: str | bytes, value: str | bytes) -> None:
        self._keys.append(self._encode_key(key))
        self._values.append(self._encode_value(value))

    def merge(self, other: HeadersImmutable | Mapping | Iterable) -> None:
        self._merge(*self._parse(other))

    def __setitem__(self, key: str | bytes, value: str | bytes) -> None:
        """
        Set the first header `key: value` and remove all other header occurrences.
        Append if not exists.
        """
        key_candidate = self._encode_key(key)
        value_candidate = self._encode_value(value)
        indexes = [id for id, key in enumerate(self._keys) if key == key_candidate]
        if indexes:
            self._values[indexes[0]] = value_candidate
            for id in reversed(indexes[1:]):
                del self._keys[id]
                del self._values[id]
        else:
            self._keys.append(key_candidate)
            self._values.append(value_candidate)

    def __delitem__(self, key: str | bytes) -> None:
        """
        Remove the header `key`.
        """
        key_candidate = self._encode_key(key)
        indexes = [id for id, key in enumerate(self._keys) if key == key_candidate]
        for id in reversed(indexes):
            del self._keys[id]
            del self._values[id]

    def _merge(self, other_keys: Iterable[bytes], other_values: Iterable[bytes]) -> None:
        self_key_positions = defaultdict(list)
        for idx, key in enumerate(self._keys):
            self_key_positions[key].append(idx)

        # Track how many times we've matched each key from `other`
        used_count = defaultdict(int)

        # Collect new pairs to append at the end
        append_keys = []
        append_values = []

        for key, value in zip(other_keys, other_values):
            if key in self_key_positions:
                occurrence_index = used_count[key]
                if occurrence_index < len(self_key_positions[key]):
                    # Replace corresponding occurrence in `a`
                    self_pos = self_key_positions[key][occurrence_index]
                    self._values[self_pos] = value
                else:
                    # Extra occurrence — append
                    append_keys.append(key)
                    append_values.append(value)

                used_count[key] += 1
            else:
                # New key — append
                append_keys.append(key)
                append_values.append(value)

        # Append new keys and extra occurrences preserving order from `b`
        self._keys.extend(append_keys)
        self._values.extend(append_values)
