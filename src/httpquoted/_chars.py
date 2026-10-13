"""Character classes of RFC 9110 section 5.6, the error type and the bytes bridge."""

from __future__ import annotations

import re
import string
from typing import AnyStr

# tchar: any VCHAR except the delimiters DQUOTE and "(),/:;<=>?@[\]{}" (section 5.6.2).
TCHAR = frozenset(string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~")
VCHAR = frozenset(chr(code) for code in range(0x21, 0x7F))
OBS_TEXT = frozenset(chr(code) for code in range(0x80, 0x100))
# What may follow a backslash, and what a sender may put between the quotes once DQUOTE
# and backslash are escaped: HTAB, SP, VCHAR and obs-text.
FIELD_TEXT = frozenset("\t ") | VCHAR | OBS_TEXT
QDTEXT = FIELD_TEXT - frozenset('"\\')
CTEXT = FIELD_TEXT - frozenset("()\\")

# Runs of plain text. A single character class with `*` never backtracks, so every scan
# stays linear however hostile the input is.
QDTEXT_RUN = re.compile(r"[\t\x20\x21\x23-\x5b\x5d-\x7e\x80-\xff]*")
CTEXT_RUN = re.compile(r"[\t\x20-\x27\x2a-\x5b\x5d-\x7e\x80-\xff]*")
LOOSE_QUOTED_RUN = re.compile(r'[^"\\]*')
LOOSE_COMMENT_RUN = re.compile(r"[^()\\]*")
TOKEN_RE = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
NOT_FIELD_TEXT = re.compile(r"[^\t\x20-\x7e\x80-\xff]")


class QuotedStringError(ValueError):
    """A value breaks the quoted-string, comment or token grammar of RFC 9110.

    `reason` names the broken rule and `offset` is the index of the offending character
    in the text that was being read or written.
    """

    def __init__(self, reason: str, offset: int) -> None:
        super().__init__(f"{reason} at offset {offset}")
        self.reason = reason
        self.offset = offset


def describe(char: str) -> str:
    """A readable name for a character in an error message."""
    return f"U+{ord(char):04X}"


def check_field_text(value: str, *, ascii_only: bool = False) -> None:
    """Raise unless every character may appear in a field value written by a sender."""
    bad = NOT_FIELD_TEXT.search(value)
    if bad is not None:
        raise QuotedStringError(f"{describe(bad.group())} is not allowed", bad.start())
    if ascii_only and not value.isascii():
        offset = next(i for i, char in enumerate(value) if not char.isascii())
        raise QuotedStringError(f"{describe(value[offset])} is obs-text", offset)


def as_text(value: str | bytes) -> str:
    """Read bytes as ISO-8859-1, where every octet maps to the code point of the same value."""
    if isinstance(value, bytes):
        return value.decode("latin-1")
    if isinstance(value, str):
        return value
    raise TypeError(f"expected str or bytes, got {type(value).__name__}")


def like(text: str, original: AnyStr) -> AnyStr:
    """Return `text` in the type of `original`: bytes in, bytes out."""
    if isinstance(original, bytes):
        return text.encode("latin-1")
    return text
