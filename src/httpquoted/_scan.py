"""Scan one quoted-string or comment inside a larger field value (RFC 9110 5.6.4, 5.6.5)."""

from __future__ import annotations

import re
from typing import AnyStr

from ._chars import (
    CTEXT_RUN,
    FIELD_TEXT,
    LOOSE_COMMENT_RUN,
    LOOSE_QUOTED_RUN,
    QDTEXT_RUN,
    QuotedStringError,
    as_text,
    check_flag,
    describe,
    like,
    type_name,
)


def scan_quoted_string(text: AnyStr, start: int = 0, *, strict: bool = False) -> tuple[AnyStr, int]:
    r"""Read the quoted-string that opens at `start` and return its value and end offset.

    The value has its quoted-pairs resolved; the offset points just past the closing
    DQUOTE. Lenient mode accepts any character between the quotes and lets an
    unterminated string run to the end of the text. `strict=True` raises
    `QuotedStringError` for a character that is not qdtext, a bad quoted-pair or a
    missing closing quote. A `start` that is not on a DQUOTE raises it too.

    >>> from httpquoted import scan_quoted_string
    >>> text = r'title="a, \"b\""; lang=en'
    >>> value, end = scan_quoted_string(text, 6, strict=True)
    >>> print(value, end, text[end:])
    a, "b" 16 ; lang=en
    """
    check_flag("strict", strict)
    source = as_text(text)
    _expect(source, start, '"', "quoted-string")
    value, end = _scan(source, start, QDTEXT_RUN if strict else LOOSE_QUOTED_RUN, strict, 0)
    return like(value, text), end


def scan_comment(text: AnyStr, start: int = 0, *, strict: bool = False) -> tuple[AnyStr, int]:
    """Read the comment that opens at `start` and return its value and end offset.

    Comments nest: the value keeps the parentheses of inner comments and has every
    quoted-pair resolved, and the offset points just past the matching ")". Inside a
    comment DQUOTE is plain text. Strict and lenient modes work as in
    `scan_quoted_string`; nesting depth is only limited by the length of the text.

    >>> from httpquoted import scan_comment
    >>> scan_comment("Mozilla/5.0 (X11; (Linux) x86_64) Gecko", 12)
    ('X11; (Linux) x86_64', 33)
    """
    check_flag("strict", strict)
    source = as_text(text)
    _expect(source, start, "(", "comment")
    value, end = _scan(source, start, CTEXT_RUN if strict else LOOSE_COMMENT_RUN, strict, 1)
    return like(value, text), end


def _expect(source: str, start: int, opener: str, rule: str) -> None:
    if isinstance(start, bool) or not isinstance(start, int):
        raise TypeError(f"start must be an int, got {type_name(start)}")
    if not 0 <= start < len(source) or source[start] != opener:
        raise QuotedStringError(f"a {rule} must start with {opener}", start)


def _scan(
    source: str, start: int, run: re.Pattern[str], strict: bool, depth: int
) -> tuple[str, int]:
    """Shared loop: depth 0 reads a quoted-string, depth 1 and more a nested comment."""
    rule = "comment" if depth else "quoted-string"
    closer = ")" if depth else '"'
    parts: list[str] = []
    pos = start + 1
    length = len(source)
    while True:
        match = run.match(source, pos)
        assert match is not None  # a pattern ending in `*` always matches
        parts.append(match.group())
        pos = match.end()
        if pos >= length:
            if strict:
                raise QuotedStringError(f"unterminated {rule}", start)
            return "".join(parts), length
        char = source[pos]
        if char == "\\":
            if pos + 1 >= length:
                if strict:
                    raise QuotedStringError("a quoted-pair needs a character", pos)
                parts.append(char)
                return "".join(parts), length
            escaped = source[pos + 1]
            if strict and escaped not in FIELD_TEXT:
                raise QuotedStringError(f"{describe(escaped)} cannot be quoted", pos + 1)
            parts.append(escaped)
            pos += 2
        elif char == closer and depth <= 1:
            return "".join(parts), pos + 1
        elif char == closer:
            depth -= 1
            parts.append(char)
            pos += 1
        elif char == "(" and depth:
            depth += 1
            parts.append(char)
            pos += 1
        else:
            raise QuotedStringError(f"{describe(char)} is not allowed in a {rule}", pos)
