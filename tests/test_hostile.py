"""Hostile input of a megabyte stays fast: every scan is linear in the length of the text.

A quadratic scan would need minutes on these inputs, so a generous wall-clock budget is
enough to catch one without making the test sensitive to a busy machine.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable

import pytest

import httpquoted as hq

SIZE = 1 << 20
BUDGET_SECONDS = 10.0

PATTERNS = {
    "backslashes": '"' + "\\" * SIZE,
    "escaped quotes": '"' + '\\"' * (SIZE // 2),
    "open parens": "(" * SIZE,
    "close parens": ")" * SIZE,
    "nested and quoted": '(\\("' * (SIZE // 4),
    "commas": "," * SIZE,
    "quotes": '"' * SIZE,
    "tiny strings": '"a",' * (SIZE // 4),
    "tiny comments": "(a)," * (SIZE // 4),
    "plain text": "a" * SIZE,
    "spaces": " " * SIZE,
}

CALLS: dict[str, Callable[[str], object]] = {
    "unquote": hq.unquote,
    "unquote strict": lambda v: hq.unquote(v, strict=True),
    "unquote_comment": hq.unquote_comment,
    "unquote_comment strict": lambda v: hq.unquote_comment(v, strict=True),
    "split_list": hq.split_list,
    "split_list comments": lambda v: hq.split_list(v, comments=True),
    "split_list strict": lambda v: hq.split_list(v, comments=True, strict=True),
    "is_token": hq.is_token,
    "bytes unquote": lambda v: hq.unquote(v.encode("latin-1"), strict=True),
    "bytes split_list": lambda v: hq.split_list(v.encode("latin-1"), comments=True),
    "bytes quote_if_needed": lambda v: hq.quote_if_needed(v.encode("latin-1")),
    "quote": hq.quote,
    "quote_comment": hq.quote_comment,
}


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("call", CALLS)
def test_hostile_input_is_handled_in_linear_time(pattern: str, call: str) -> None:
    started = time.perf_counter()
    with contextlib.suppress(hq.QuotedStringError):
        CALLS[call](PATTERNS[pattern])
    assert time.perf_counter() - started < BUDGET_SECONDS


@pytest.mark.parametrize("pattern", ["(", '"', "\\"])
def test_scanners_handle_a_megabyte_of_openers_and_backslashes(pattern: str) -> None:
    text = pattern * SIZE
    started = time.perf_counter()
    for scan in (hq.scan_quoted_string, hq.scan_comment):
        for strict in (False, True):
            with contextlib.suppress(hq.QuotedStringError):
                scan(text, 0, strict=strict)
    assert time.perf_counter() - started < BUDGET_SECONDS
