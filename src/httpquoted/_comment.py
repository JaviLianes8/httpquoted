"""Quote and unquote HTTP comments (RFC 9110 section 5.6.5)."""

from __future__ import annotations

from typing import AnyStr

from ._chars import QuotedStringError, as_text, check_field_text, like
from ._quote import _unescape
from ._scan import scan_comment


def quote_comment(value: AnyStr, *, ascii_only: bool = False) -> AnyStr:
    """Wrap a value in parentheses, escaping parentheses and backslash.

    Every "(", ")" and backslash in the value becomes a quoted-pair, the only ones
    section 5.6.4 lets a sender write in a comment, so the result reads back with
    :func:`unquote_comment` as the same text and never opens a nested comment. The
    characters refused are the ones :func:`quote` refuses.
    """
    text = as_text(value)
    check_field_text(text, ascii_only=ascii_only)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return like(f"({escaped})", value)


def unquote_comment(value: AnyStr, *, strict: bool = False) -> AnyStr:
    """Strip the outer parentheses of a comment and resolve its quoted-pairs.

    Nested comments stay in the result as text, parentheses included. Lenient by
    default: a value not wrapped in parentheses comes back unchanged. With
    `strict=True` the value must be exactly one comment, balanced and made of ctext,
    quoted-pairs and nested comments; anything else raises `QuotedStringError`.
    """
    text = as_text(value)
    if strict:
        result, end = scan_comment(text, strict=True)
        if end != len(text):
            raise QuotedStringError("text after the closing parenthesis", end)
        return like(result, value)
    if len(text) >= 2 and text[0] == "(" and text[-1] == ")":
        return like(_unescape(text[1:-1]), value)
    return value
