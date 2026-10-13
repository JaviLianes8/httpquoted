"""Quote and unquote HTTP quoted-string field values (RFC 9110 section 5.6.4)."""

from __future__ import annotations

import re
from typing import AnyStr

from ._chars import TOKEN_RE, QuotedStringError, as_text, check_field_text, like
from ._scan import scan_quoted_string

_QUOTED_PAIR = re.compile(r"\\(.)", re.DOTALL)


def quote(value: AnyStr, *, ascii_only: bool = False) -> AnyStr:
    """Wrap a value in a quoted-string, escaping backslash and double quote.

    Only those two characters become quoted-pairs, as section 5.6.4 asks of senders,
    so the result parses back to the original with :func:`unquote`. A character a
    quoted-string cannot carry (CR, LF, NUL and the other controls, DEL, anything above
    U+00FF) raises `QuotedStringError` instead of reaching the header; `ascii_only=True`
    also refuses obs-text (U+0080 to U+00FF). Accepts `str` or `bytes`.
    """
    text = as_text(value)
    check_field_text(text, ascii_only=ascii_only)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return like(f'"{escaped}"', value)


def quote_if_needed(value: AnyStr, *, ascii_only: bool = False) -> AnyStr:
    """Return a token unchanged and quote anything else (a parameter value, 5.6.6)."""
    if TOKEN_RE.fullmatch(as_text(value)):
        return value
    return quote(value, ascii_only=ascii_only)


def unquote(value: AnyStr, *, strict: bool = False) -> AnyStr:
    """Strip the surrounding quotes and resolve quoted-pairs.

    Lenient by default: a value that is not wrapped in double quotes is returned
    unchanged, so a bare token passes through untouched, and the inside of a quoted
    value is unescaped without further checks. With `strict=True` the value must be
    exactly a token or a quoted-string (the `token / quoted-string` choice of a
    parameter value); anything else raises `QuotedStringError`.
    """
    text = as_text(value)
    if strict:
        return like(_strict_unquote(text), value)
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return like(_unescape(text[1:-1]), value)
    return value


def _strict_unquote(text: str) -> str:
    if text.startswith('"'):
        result, end = scan_quoted_string(text, strict=True)
        if end != len(text):
            raise QuotedStringError("text after the closing quote", end)
        return result
    if TOKEN_RE.fullmatch(text):
        return text
    bad = TOKEN_RE.match(text)
    raise QuotedStringError("not a token or a quoted-string", bad.end() if bad else 0)


def _unescape(inner: str) -> str:
    # A trailing lone backslash has nothing to quote and is kept as it is.
    return _QUOTED_PAIR.sub(r"\1", inner)
