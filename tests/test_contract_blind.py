"""Contracts added after the blind mutation round and the review: each pins an unheld promise."""

from __future__ import annotations

import io
import sys
from collections.abc import Callable

import pytest

import httpquoted as hq
from httpquoted._cli import main


@pytest.mark.parametrize("encode", [hq.quote, hq.quote_comment, hq.quote_if_needed])
@pytest.mark.parametrize("ascii_only", [False, True])
def test_del_is_refused_with_or_without_ascii_only(
    encode: Callable[..., str], ascii_only: bool
) -> None:
    with pytest.raises(hq.QuotedStringError) as caught:
        encode("a\x7f", ascii_only=ascii_only)
    assert (caught.value.reason, caught.value.offset) == ("U+007F is not allowed", 1)


def test_text_already_on_stdout_stays_before_the_octets(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="latin-1", newline="\n")
    monkeypatch.setattr(sys, "stdout", out)
    out.write("x\n")
    assert main(["quote", "a"]) == 0
    out.flush()
    assert raw.getvalue() == b'x\n"a"\n'


def test_a_value_that_is_not_octets_is_named_by_its_first_bad_character(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="latin-1"))
    assert main(["split", "\u20ac\u2603"]) == 1
    assert capsys.readouterr().err == "httpquoted: U+20AC is not an ISO-8859-1 octet\n"


def test_a_posix_separator_is_read_as_octets_like_the_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # On POSIX the octets of "\xe9" in UTF-8 are two characters, so the separator is refused.
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "argv", ["httpquoted", "split", "--separator", "\xe9", "a\xe9b"])
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 2


@pytest.mark.parametrize("value", ["[a)", "x(a)", "a)"])
def test_lenient_unquote_comment_needs_both_parentheses(value: str) -> None:
    assert hq.unquote_comment(value) == value
    assert hq.unquote_comment(value.encode()) == value.encode()


def test_only_one_carriage_return_of_a_crlf_line_is_removed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"a\r\r\n"), encoding="latin-1"))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="latin-1"))
    assert main(["quote"]) == 1
    assert capsys.readouterr().err == "httpquoted: U+000D is not allowed at offset 1\n"
