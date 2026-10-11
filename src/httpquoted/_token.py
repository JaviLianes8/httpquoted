"""Recognise an HTTP token (RFC 9110 section 5.6.2, the tchar production)."""

from __future__ import annotations

import string

_SPECIALS = "!#$%&'*+-.^_`|~"
_TCHARS = frozenset(string.ascii_letters + string.digits + _SPECIALS)


def is_token(value: str) -> bool:
    """Report whether a value is a non-empty run of token characters.

    A token needs at least one character and may contain only tchar: letters,
    digits and a fixed set of symbols. Anything else, including an empty string,
    whitespace or a delimiter, is not a token.
    """
    return bool(value) and all(char in _TCHARS for char in value)
