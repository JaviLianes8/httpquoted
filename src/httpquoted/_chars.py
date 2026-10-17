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
NOT_ASCII_TEXT = re.compile(r"[^\t\x20-\x7e]")


class QuotedStringError(ValueError):
    r"""A value breaks the quoted-string, comment or token grammar of RFC 9110.

    `reason` names the broken rule and `offset` is the index of the offending character
    in the text that was being read or written. The message never quotes the input.

    >>> from httpquoted import QuotedStringError, quote
    >>> try:
    ...     quote("a\nb")
    ... except QuotedStringError as error:
    ...     print(error.reason, error.offset, isinstance(error, ValueError))
    U+000A is not allowed 1 True
    """

    def __init__(self, reason: str, offset: int) -> None:
        super().__init__(f"{reason} at offset {offset}")
        self.reason = reason
        self.offset = offset

    def __reduce__(self) -> tuple[type[QuotedStringError], tuple[str, int]]:
        return type(self), (self.reason, self.offset)


def type_name(value: object) -> str:
    """The type name of a value for an error message, at most 40 characters."""
    # The name slot of the type itself: a metaclass property cannot replace or inflate it.
    name = type.__dict__["__name__"].__get__(type(value))
    return str.__getitem__(name, slice(0, 40)) if isinstance(name, str) else "object"


def check_flag(name: str, value: object) -> None:
    """Raise TypeError unless an option is a real bool."""
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool, got {type_name(value)}")


def describe(char: str) -> str:
    """A readable name for a character in an error message."""
    return f"U+{ord(char):04X}"


def check_field_text(value: str, *, ascii_only: bool = False) -> None:
    """Raise unless every character may appear in a field value written by a sender."""
    bad = (NOT_ASCII_TEXT if ascii_only else NOT_FIELD_TEXT).search(value)
    if bad is None:
        return
    char = bad.group()
    kind = "is obs-text" if char in OBS_TEXT else "is not allowed"
    raise QuotedStringError(f"{describe(char)} {kind}", bad.start())


def as_text(value: str | bytes) -> str:
    """Read bytes as ISO-8859-1, where every octet maps to the code point of the same value."""
    # Unbound base methods give an exact str, so a subclass cannot override what is read.
    if isinstance(value, bytes):
        return bytes.decode(value, "latin-1")
    if isinstance(value, str):
        return str.__str__(value)
    raise TypeError(f"expected str or bytes, got {type_name(value)}")


def like(text: str, original: AnyStr) -> AnyStr:
    """Return `text` in the type of `original`: bytes in, bytes out."""
    if isinstance(original, bytes):
        return text.encode("latin-1")
    return text
