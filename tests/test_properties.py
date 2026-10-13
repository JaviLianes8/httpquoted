"""Seeded property tests: round trips and agreement between modes over random values."""

from __future__ import annotations

import random
from collections.abc import Callable

import pytest

import httpquoted as hq

FIELD_TEXT = "\t" + "".join(chr(c) for c in [*range(0x20, 0x7F), *range(0x80, 0x100)])
# Characters with a job in the grammar, weighted so most values contain several.
MEANINGFUL = '"\\(),; \t'
ANY = "".join(chr(c) for c in range(0x100)) + "\u0100\u20ac"
ROUNDS = 400


def _values(rng: random.Random, alphabet: str) -> list[str]:
    pool = alphabet + MEANINGFUL * 8
    return ["".join(rng.choices(pool, k=rng.randrange(12))) for _ in range(ROUNDS)]


@pytest.fixture
def rng(request: pytest.FixtureRequest) -> random.Random:
    return random.Random(request.node.name)


def test_quote_then_strict_unquote_is_the_identity(rng: random.Random) -> None:
    for value in _values(rng, FIELD_TEXT):
        assert hq.unquote(hq.quote(value), strict=True) == value
        assert hq.unquote(hq.quote(value)) == value
        assert hq.unquote(hq.quote_if_needed(value), strict=True) == value


def test_quote_comment_then_strict_unquote_comment_is_the_identity(rng: random.Random) -> None:
    for value in _values(rng, FIELD_TEXT):
        assert hq.unquote_comment(hq.quote_comment(value), strict=True) == value


def test_scanners_stop_exactly_after_the_quoted_form(rng: random.Random) -> None:
    for value in _values(rng, FIELD_TEXT):
        for encode, scan in (
            (hq.quote, hq.scan_quoted_string),
            (hq.quote_comment, hq.scan_comment),
        ):
            written = encode(value)
            for strict in (True, False):
                assert scan("x " + written + ' ")(', 2, strict=strict) == (value, 2 + len(written))


def test_split_list_finds_every_quoted_element(rng: random.Random) -> None:
    values = _values(rng, FIELD_TEXT)
    for size in (1, 2, 5):
        for start in range(0, ROUNDS - size, size):
            chunk = values[start : start + size]
            quoted = [hq.quote(v) for v in chunk]
            assert hq.split_list(" , ".join(quoted), strict=True) == quoted
            assert hq.split_list(";".join(quoted), separator=";", strict=True) == quoted
            comments = [hq.quote_comment(v) for v in chunk]
            assert hq.split_list(",".join(comments), comments=True, strict=True) == comments


def test_bytes_and_str_give_the_same_answer(rng: random.Random) -> None:
    for value in _values(rng, FIELD_TEXT):
        octets = value.encode("latin-1")
        assert hq.quote(octets) == hq.quote(value).encode("latin-1")
        assert hq.quote_comment(octets) == hq.quote_comment(value).encode("latin-1")
        assert hq.unquote(octets) == hq.unquote(value).encode("latin-1")
        assert hq.is_token(octets) is hq.is_token(value)
        split = [e.encode("latin-1") for e in hq.split_list(value, comments=True)]
        assert hq.split_list(octets, comments=True) == split


STRICT_CALLS: list[tuple[Callable[..., object], dict[str, bool]]] = [
    (hq.unquote, {}),
    (hq.unquote_comment, {}),
    (hq.split_list, {}),
    (hq.split_list, {"comments": True}),
]


def test_lenient_functions_never_raise_and_strict_ones_raise_only_the_library_error(
    rng: random.Random,
) -> None:
    for value in _values(rng, ANY):
        for function, options in STRICT_CALLS:
            function(value, **options)
            try:
                function(value, strict=True, **options)
            except hq.QuotedStringError as error:
                assert 0 <= error.offset <= len(value)
        try:
            hq.quote(value)
        except hq.QuotedStringError as error:
            assert 0 <= error.offset < len(value)


def test_strict_and_lenient_agree_whenever_strict_accepts(rng: random.Random) -> None:
    for value in _values(rng, FIELD_TEXT):
        for function, options in STRICT_CALLS:
            for candidate in (value, '"' + value + '"', "(" + value + ")"):
                try:
                    accepted = function(candidate, strict=True, **options)
                except hq.QuotedStringError:
                    continue
                assert function(candidate, **options) == accepted


def test_a_valid_value_is_never_a_token_and_a_quoted_string_at_once(rng: random.Random) -> None:
    for value in _values(rng, FIELD_TEXT):
        assert hq.needs_quoting(value) is not hq.is_token(value)
        if hq.is_token(value):
            assert hq.quote_if_needed(value) == value
        else:
            assert hq.quote_if_needed(value) == hq.quote(value)
