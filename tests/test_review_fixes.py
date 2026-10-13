"""Regression tests for the findings of the independent review of this round."""

from __future__ import annotations

import io
import sys

import pytest

import httpquoted as hq
from httpquoted._cli import main


def _cli(monkeypatch: pytest.MonkeyPatch, *args: str, stdin: bytes = b"") -> tuple[int, bytes]:
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin), encoding="cp1252"))
    monkeypatch.setattr(sys, "stdout", out)
    status = main(list(args))
    out.flush()
    buffer = out.buffer
    assert isinstance(buffer, io.BytesIO)
    return status, buffer.getvalue()


def test_cli_reads_and_writes_octets_as_iso_8859_1(monkeypatch: pytest.MonkeyPatch) -> None:
    status, out = _cli(monkeypatch, "quote", stdin=b"caf\xc3\xa9\r\n\x81\n")
    assert (status, out) == (0, b'"caf\xc3\xa9"\n"\x81"\n')


def test_cli_writes_obs_text_the_locale_cannot_encode(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _cli(monkeypatch, "quote", "a\x81b") == (0, b'"a\x81b"\n')


def test_cli_keeps_a_next_line_character_inside_one_value(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _cli(monkeypatch, "split", stdin=b"a\x85b, c\n") == (0, b"a\x85b\nc\n")


def test_cli_refuses_output_that_is_not_an_octet(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(monkeypatch, "unquote", "\u20ac") == (1, b"")
    assert capsys.readouterr().err == "httpquoted: U+20AC is not an ISO-8859-1 octet\n"


def test_split_list_takes_a_bytes_separator() -> None:
    assert hq.split_list(b'a;"b;c"', separator=b";") == [b"a", b'"b;c"']
    assert hq.split_list('a;"b;c"', separator=b";") == ["a", '"b;c"']


@pytest.mark.parametrize("separator", ["\u20ac", "\x00", "\n", b"\x7f", b";;"])
def test_split_list_refuses_a_separator_that_is_not_one_field_character(
    separator: str | bytes,
) -> None:
    with pytest.raises(ValueError, match="one field character"):
        hq.split_list(b"a,b", separator=separator)


@pytest.mark.parametrize(
    ("value", "reason", "offset"),
    [
        ("ab\u00e9\u0100", "U+00E9 is obs-text", 2),
        ("\u00e9\x00", "U+00E9 is obs-text", 0),
        ("a\x00\u00e9", "U+0000 is not allowed", 1),
    ],
)
def test_ascii_only_reports_the_first_refused_character(
    value: str, reason: str, offset: int
) -> None:
    for encode in (hq.quote, hq.quote_comment):
        with pytest.raises(hq.QuotedStringError) as caught:
            encode(value, ascii_only=True)
        assert (caught.value.reason, caught.value.offset) == (reason, offset)


@pytest.mark.parametrize("start", [True, 1.0, "1"])
def test_scanners_refuse_a_start_that_is_not_an_int(start: object) -> None:
    for scan in (hq.scan_quoted_string, hq.scan_comment):
        with pytest.raises(TypeError, match="start must be an int"):
            scan('x"y"', start)  # type: ignore[arg-type]


def test_the_end_offset_gives_the_raw_comment_for_reparsing() -> None:
    text = "ua (a (b \\) c) d) rest"
    value, end = hq.scan_comment(text, 3, strict=True)
    assert value == "a (b ) c) d"
    raw = text[3:end]
    assert raw == "(a (b \\) c) d)"
    assert hq.scan_comment(raw, strict=True) == (value, len(raw))


@pytest.mark.parametrize(
    "value",
    ['"' + "\\" * 4096, "(" * 4096, '"a",' * 1024, "(a)," * 1024],
)
def test_bytes_input_takes_the_same_paths(value: str) -> None:
    octets = value.encode("latin-1")
    assert hq.split_list(octets, comments=True) == [
        e.encode("latin-1") for e in hq.split_list(value, comments=True)
    ]
    assert hq.unquote(octets) == hq.unquote(value).encode("latin-1")
    assert hq.quote_if_needed(octets) == hq.quote_if_needed(value).encode("latin-1")
