"""Split a delimited header value while respecting quoted-strings and comments."""

from __future__ import annotations

import re
from typing import AnyStr

from ._chars import FIELD_TEXT, NOT_FIELD_TEXT, QuotedStringError, as_text, describe, like
from ._scan import scan_comment, scan_quoted_string

_RESERVED = frozenset('"\\()')


def split_list(
    header: AnyStr,
    *,
    separator: str | bytes = ",",
    comments: bool = False,
    strict: bool = False,
) -> list[AnyStr]:
    """Split a list-style header on separators that sit outside quoted-strings.

    A separator inside double quotes is part of the value, and a quoted-pair never ends
    the quotes. With `comments=True` a parenthesised comment (in Via, User-Agent or
    Server) is skipped as a unit too, nested or not, and a DQUOTE inside it is plain
    text. Each element is trimmed of surrounding spaces and tabs, and empty elements
    are dropped, as section 5.6.1.2 asks of recipients. `separator` is "," for lists
    and ";" for parameters, as `str` or `bytes`. Elements keep their quotes.

    Lenient by default: an unterminated quoted-string or comment runs to the end. With
    `strict=True`, `QuotedStringError` is raised for a character that is not field
    content (CR, LF, NUL, other controls, DEL), a quoted-string or comment that breaks
    its grammar or never ends, and a stray ")" when `comments=True`. The grammar of
    each element belongs to the field and is left to the caller: `"a"b` is one element.
    """
    separator = check_separator(separator)
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


def check_separator(separator: str | bytes) -> str:
    """Return the separator as text, or raise ValueError if it cannot split a field value."""
    sep = as_text(separator)
    if len(sep) != 1 or sep in _RESERVED or sep not in FIELD_TEXT:
        raise ValueError(
            "separator must be one field character other than DQUOTE, backslash, ( or )"
        )
    return sep


def _keep(element: str, header: AnyStr, elements: list[AnyStr]) -> None:
    element = element.strip(" \t")
    if element:
        elements.append(like(element, header))
