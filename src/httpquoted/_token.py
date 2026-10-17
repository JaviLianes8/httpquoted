"""Recognise an HTTP token (RFC 9110 section 5.6.2, the tchar production)."""

from __future__ import annotations

from typing import AnyStr

from ._chars import TOKEN_RE, as_text


def is_token(value: AnyStr) -> bool:
    """Report whether a value is a non-empty run of token characters.

    A token needs at least one character and may contain only tchar: letters,
    digits and a fixed set of symbols. Anything else, including an empty string,
    whitespace or a delimiter, is not a token. Accepts `str` or `bytes`.

    >>> from httpquoted import is_token
    >>> is_token("max-age"), is_token(b"gzip"), is_token("a b"), is_token("")
    (True, True, False, False)
    """
    return TOKEN_RE.fullmatch(as_text(value)) is not None


def needs_quoting(value: AnyStr) -> bool:
    """Report whether a parameter value must be sent as a quoted-string.

    RFC 9110 section 5.6.6 lets a value that is a token travel bare or quoted with the
    same meaning; anything else, the empty value included, needs the quotes.

    >>> from httpquoted import needs_quoting
    >>> needs_quoting("utf-8"), needs_quoting("two words"), needs_quoting("")
    (False, True, True)
    """
    return not is_token(value)
