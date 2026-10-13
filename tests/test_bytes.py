"""Bytes in, bytes out: octets are read as ISO-8859-1, so obs-text survives unchanged."""

import pytest

import httpquoted as hq


def test_quote_and_unquote_keep_bytes_as_bytes() -> None:
    quoted = hq.quote(b'caf\xe9 "x"')
    assert quoted == b'"caf\xe9 \\"x\\""'
    assert hq.unquote(quoted) == b'caf\xe9 "x"'
    assert hq.unquote(quoted, strict=True) == b'caf\xe9 "x"'
    assert hq.unquote(b"token") == b"token"


def test_every_octet_of_obs_text_round_trips() -> None:
    octets = bytes(range(0x80, 0x100))
    assert hq.unquote(hq.quote(octets), strict=True) == octets
    assert hq.unquote_comment(hq.quote_comment(octets), strict=True) == octets


def test_quote_refuses_control_octets_and_obs_text_when_ascii_only() -> None:
    with pytest.raises(hq.QuotedStringError):
        hq.quote(b"a\r\nb")
    with pytest.raises(hq.QuotedStringError):
        hq.quote(b"\xe9", ascii_only=True)


def test_token_checks_accept_bytes() -> None:
    assert hq.is_token(b"max-age") is True
    assert hq.is_token(b"a b") is False
    assert hq.needs_quoting(b"") is True
    assert hq.quote_if_needed(b"gzip") == b"gzip"
    assert hq.quote_if_needed(b"a b") == b'"a b"'


def test_scanners_return_bytes_and_octet_offsets() -> None:
    assert hq.scan_quoted_string(b'x="\xe9\\"", y', 2) == (b'\xe9"', 7)
    assert hq.scan_comment(b"a (b (\xff)) c", 2, strict=True) == (b"b (\xff)", 9)


def test_split_list_returns_bytes_elements() -> None:
    value = b'gzip, "a,\xe9", (x, y) br'
    assert hq.split_list(value, comments=True) == [b"gzip", b'"a,\xe9"', b"(x, y) br"]


def test_comment_codec_keeps_bytes() -> None:
    assert hq.quote_comment(b"a(b") == b"(a\\(b)"
    assert hq.unquote_comment(b"(a\\(b)") == b"a(b"
    assert hq.unquote_comment(b"abc") == b"abc"


@pytest.mark.parametrize(
    "call",
    [hq.quote, hq.unquote, hq.is_token, hq.split_list, hq.scan_comment, hq.quote_comment],
)
def test_other_types_raise_type_error(call: object) -> None:
    with pytest.raises(TypeError, match="expected str or bytes"):
        call(123)  # type: ignore[operator]


def test_bytearray_is_not_silently_accepted() -> None:
    with pytest.raises(TypeError):
        hq.quote(bytearray(b"x"))  # type: ignore[type-var]
