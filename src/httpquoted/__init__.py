"""Typed codec for the HTTP quoted-string and comment primitives (RFC 9110)."""

from __future__ import annotations

from ._chars import QuotedStringError
from ._comment import quote_comment, unquote_comment
from ._quote import quote, quote_if_needed, unquote
from ._scan import scan_comment, scan_quoted_string
from ._split import split_list
from ._token import is_token, needs_quoting

__version__ = "0.2.0"

__all__ = [
    "QuotedStringError",
    "is_token",
    "needs_quoting",
    "quote",
    "quote_comment",
    "quote_if_needed",
    "scan_comment",
    "scan_quoted_string",
    "split_list",
    "unquote",
    "unquote_comment",
]
