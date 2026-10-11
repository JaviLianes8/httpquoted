"""Quote and unquote HTTP quoted-string field values (RFC 9110 section 5.6.4)."""

from __future__ import annotations


def quote(value: str) -> str:
    """Wrap a value in a quoted-string, escaping backslash and double quote.

    The two characters that carry meaning inside a quoted-string, the backslash
    and the double quote, are emitted as quoted-pairs so the result parses back
    to the original with :func:`unquote`.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def unquote(value: str) -> str:
    """Strip the surrounding quotes and resolve quoted-pairs.

    A value that is not wrapped in double quotes is returned unchanged, so a bare
    token passes through untouched.
    """
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return _unescape(value[1:-1])
    return value


def _unescape(inner: str) -> str:
    out: list[str] = []
    i = 0
    length = len(inner)
    while i < length:
        char = inner[i]
        if char == "\\" and i + 1 < length:
            out.append(inner[i + 1])
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)
