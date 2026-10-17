"""Hostile arguments cannot steer a result, break the error contract or crash the command."""

from __future__ import annotations

import errno
import io
import sys
from typing import Any, NoReturn

import pytest

import httpquoted as hq
from httpquoted import _cli as cli_module
from httpquoted._cli import main


def _boom(*args: object, **kwargs: object) -> NoReturn:
    raise RuntimeError("hostile method called")


class HostileStr(str):
    replace = _boom
    startswith = _boom
    strip = _boom
    __len__ = _boom
    __getitem__ = _boom
    __iter__ = _boom
    __str__ = _boom


class HostileBytes(bytes):
    decode = _boom
    __len__ = _boom
    __getitem__ = _boom


class HostileInt(int):
    __add__ = _boom
    __lt__ = _boom
    __le__ = _boom
    __gt__ = _boom
    __ge__ = _boom
    __eq__ = _boom
    __index__ = _boom
    __format__ = _boom
    __hash__ = int.__hash__


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        (lambda v: hq.quote(v), '"a \\"b\\" (c)"'),
        (lambda v: hq.quote_comment(v), '(a "b" \\(c\\))'),
        (lambda v: hq.quote_if_needed(v), '"a \\"b\\" (c)"'),
        (lambda v: hq.is_token(v), False),
        (lambda v: hq.needs_quoting(v), True),
        (lambda v: hq.split_list(v, comments=True), ['a "b" (c)']),
        (lambda v: hq.split_list("x;y", separator=HostileStr(";")), ["x", "y"]),
    ],
)
def test_str_subclass_methods_are_never_called(call: Any, expected: object) -> None:
    assert call(HostileStr('a "b" (c)')) == expected


def test_readers_ignore_subclass_methods() -> None:
    assert hq.unquote(HostileStr('"a\\"b"'), strict=True) == 'a"b'
    assert hq.unquote(HostileStr('"a\\"b"')) == 'a"b'
    assert hq.unquote_comment(HostileStr("(a (b))"), strict=True) == "a (b)"
    assert hq.scan_quoted_string(HostileStr('x"y"z'), 1) == ("y", 4)
    assert hq.scan_comment(HostileStr("(y)"), strict=True) == ("y", 3)
    assert hq.unquote(HostileBytes(b'"caf\xe9"'), strict=True) == b"caf\xe9"
    assert hq.quote(HostileBytes(b"a")) == b'"a"'
    assert hq.split_list(HostileBytes(b"a, b")) == [b"a", b"b"]


def test_an_int_subclass_start_cannot_steer_the_scan_or_the_message() -> None:
    assert hq.scan_quoted_string('"abc"', HostileInt(0)) == ("abc", 5)
    assert hq.scan_comment("x(a)", HostileInt(1)) == ("a", 4)

    class LyingInt(int):
        def __int__(self) -> int:
            return 0

    assert hq.scan_quoted_string('a="b"', LyingInt(2)) == ("b", 5)
    with pytest.raises(hq.QuotedStringError) as caught:
        hq.scan_quoted_string("xyz", HostileInt(1))
    assert type(caught.value.offset) is int
    assert str(caught.value) == 'a quoted-string must start with " at offset 1'


@pytest.mark.parametrize(
    ("start", "offset"),
    [(10**5000, 3), (-(10**5000), 0), (-1, 0), (9, 3)],
    ids=["huge", "huge negative", "minus one", "past the end"],
)
def test_a_start_outside_the_text_is_reported_at_the_nearest_end(start: int, offset: int) -> None:
    for scan, rule in (
        (hq.scan_quoted_string, 'quoted-string must start with "'),
        (
            hq.scan_comment,
            "comment must start with (",
        ),
    ):
        with pytest.raises(hq.QuotedStringError) as caught:
            scan("abc", start)
        assert caught.value.offset == offset
        assert str(caught.value) == f"a {rule} at offset {offset}"


def test_a_metaclass_cannot_inflate_or_break_a_type_name() -> None:
    class Inflated(str):
        def __getitem__(self, key: object) -> str:
            return "X" * 1_000_000

        __str__ = _boom

    meta = type("Meta", (type,), {"__name__": property(_boom)})
    odd = meta("Odd", (), {})()
    with pytest.raises(TypeError, match=r"got Odd$"):
        hq.quote(odd)
    inflated = type("T", (), {})
    inflated.__name__ = Inflated("N" * 100)
    with pytest.raises(TypeError) as caught:
        hq.quote(inflated())
    assert str(caught.value) == "expected str or bytes, got " + "N" * 40


def _cli(monkeypatch: pytest.MonkeyPatch, *args: str, **streams: object) -> int:
    for name, stream in streams.items():
        monkeypatch.setattr(sys, name, stream)
    return main(list(args))


def test_a_closed_standard_input_reads_as_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    assert _cli(monkeypatch, "quote", stdin=None, stdout=out) == 0
    assert out.getvalue() == ""


def test_a_closed_standard_output_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    assert _cli(monkeypatch, "quote", "a", stdout=None, stderr=err) == 1
    assert err.getvalue() == ""


def test_a_closed_standard_error_never_mixes_into_the_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = io.StringIO()
    assert _cli(monkeypatch, "quote", "ok", "a\x01b", stdout=out, stderr=None) == 1
    assert out.getvalue() == '"ok"\n'


class _FullDisk(io.StringIO):
    def write(self, text: str) -> int:
        raise OSError(errno.ENOSPC, "no space left on device")


def test_a_write_error_is_reported_without_a_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    err = io.StringIO()
    silenced: list[bool] = []
    monkeypatch.setattr(cli_module, "_silence_stdout", lambda: silenced.append(True))
    assert _cli(monkeypatch, "quote", "a", stdout=_FullDisk(), stderr=err) == 1
    # The unwritten bytes must not be flushed again at exit, which would fail with a traceback.
    assert silenced == [True]
    assert err.getvalue() == f"httpquoted: cannot write the output (errno {errno.ENOSPC})\n"
