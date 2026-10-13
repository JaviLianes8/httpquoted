"""Split a delimited header value while respecting quoted-strings and comments."""

from __future__ import annotations

import re
from typing import AnyStr

from ._chars import NOT_FIELD_TEXT, QuotedStringError, as_text, describe, like
from ._scan import scan_comment, scan_quoted_string

_RESERVED = frozenset('"\\()')


def split_list(
    header: AnyStr, *, separator: str = ",", comments: bool = False, strict: bool = False
) -> list[AnyStr]:
    """Split a list-style header on separators that sit outside quoted-strings.

    A separator inside double quotes is part of the value, and a quoted-pair never ends
    the quotes. With `comments=True` a parenthesised comment (in Via, User-Agent or
    Server) is skipped as a unit too, nested or not, and a DQUOTE inside it is plain
    text. Each element is trimmed of surrounding spaces and tabs, and empty elements
    are dropped, as section 5.6.1.2 asks of recipients. `separator` is "," for lists
    and ";" for parameters. Elements keep their quotes; `unquote` them as needed.

    Lenient by default: an unterminated quoted-string or comment runs to the end. With
    `strict=True` that, a stray ")" and any character that is not field content (CR,
    LF, NUL, other controls) raise `QuotedStringError`.
    """
    if len(separator) != 1 or separator in _RESERVED:
        raise ValueError("separator must be one character other than DQUOTE, backslash, ( or )")
    text = as_text(header)
    if strict:
        bad = NOT_FIELD_TEXT.search(text)
        if bad is not None:
            raise QuotedStringError(f"{describe(bad.group())} is not allowed", bad.start())
    stops = re.compile("[" + re.escape(separator + '"' + ("()" if comments else "")) + "]")
    elements: list[AnyStr] = []
    begin = pos = 0
    length = len(text)
    while pos < length:
        found = stops.search(text, pos)
        if found is None:
            break
        pos = found.start()
        char = text[pos]
        if char == separator:
            _keep(text[begin:pos], header, elements)
            begin = pos = pos + 1
        elif char == '"':
            pos = scan_quoted_string(text, pos, strict=strict)[1]
        elif char == "(":
            pos = scan_comment(text, pos, strict=strict)[1]
        elif strict:
            raise QuotedStringError("unbalanced )", pos)
        else:
            pos += 1
    _keep(text[begin:], header, elements)
    return elements


def _keep(element: str, header: AnyStr, elements: list[AnyStr]) -> None:
    element = element.strip(" \t")
    if element:
        elements.append(like(element, header))
