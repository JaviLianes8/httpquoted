import pytest

from httpquoted import QuotedStringError, needs_quoting, quote, quote_if_needed, unquote


def test_quote_wraps_a_plain_value_in_double_quotes() -> None:
    assert quote("gzip") == '"gzip"'


def test_quote_escapes_an_embedded_double_quote() -> None:
    assert quote('a"b') == '"a\\"b"'


def test_quote_escapes_a_backslash() -> None:
    assert quote("a\\b") == '"a\\\\b"'


def test_quote_handles_the_empty_value() -> None:
    assert quote("") == '""'


def test_quote_leaves_other_delimiters_and_whitespace_unescaped() -> None:
    assert quote("a b\t(c), d;e=f") == '"a b\t(c), d;e=f"'


@pytest.mark.parametrize(
    ("value", "offset"),
    [("a\r\nX-Evil: 1", 1), ("\n", 0), ("a\x00", 1), ("\x7f", 0), ("ab\x1f", 2), ("\u20ac", 0)],
)
def test_quote_refuses_characters_a_quoted_string_cannot_carry(value: str, offset: int) -> None:
    with pytest.raises(QuotedStringError) as caught:
        quote(value)
    assert caught.value.offset == offset
    assert isinstance(caught.value, ValueError)


def test_quote_accepts_obs_text_unless_ascii_only() -> None:
    assert quote("caf\u00e9") == '"caf\u00e9"'
    with pytest.raises(QuotedStringError, match="obs-text at offset 3"):
        quote("caf\u00e9", ascii_only=True)


def test_quote_if_needed_leaves_a_token_bare() -> None:
    assert quote_if_needed("utf-8") == "utf-8"


def test_quote_if_needed_quotes_anything_else() -> None:
    assert quote_if_needed("a b") == '"a b"'
    assert quote_if_needed("") == '""'
    assert quote_if_needed("caf\u00e9") == '"caf\u00e9"'


def test_quote_if_needed_honours_ascii_only() -> None:
    with pytest.raises(QuotedStringError):
        quote_if_needed("caf\u00e9", ascii_only=True)


def test_needs_quoting_is_true_for_anything_but_a_token() -> None:
    assert needs_quoting("max-age") is False
    assert needs_quoting("a b") is True
    assert needs_quoting("") is True


def test_unquote_strips_the_surrounding_quotes() -> None:
    assert unquote('"gzip"') == "gzip"


def test_unquote_resolves_an_escaped_double_quote() -> None:
    assert unquote('"a\\"b"') == 'a"b'


def test_unquote_resolves_any_quoted_pair() -> None:
    assert unquote('"\\a\\\\\\ b"') == "a\\ b"


def test_lenient_unquote_resolves_a_quoted_pair_of_any_character() -> None:
    assert unquote('"a\\\nb\\\r"') == "a\nb\r"


def test_unquote_returns_a_bare_token_unchanged() -> None:
    assert unquote("gzip") == "gzip"


def test_unquote_handles_the_empty_quoted_string() -> None:
    assert unquote('""') == ""


def test_lenient_unquote_keeps_the_0_1_behaviour_on_malformed_input() -> None:
    assert unquote('"a"b"') == 'a"b'
    assert unquote('"a\\"') == "a\\"
    assert unquote('"abc') == '"abc'
    assert unquote('"') == '"'


def test_strict_unquote_accepts_a_token_or_a_quoted_string() -> None:
    assert unquote("utf-8", strict=True) == "utf-8"
    assert unquote('"a\\"b c"', strict=True) == 'a"b c'


@pytest.mark.parametrize(
    ("value", "reason", "offset"),
    [
        ('"a"b"', "text after the closing quote", 3),
        ('"a\\"', "unterminated quoted-string", 0),
        ('"abc', "unterminated quoted-string", 0),
        ('"a\nb"', "U+000A is not allowed in a quoted-string", 2),
        ('"a\\\nb"', "U+000A cannot be quoted", 3),
        ('"a\\', "a quoted-pair needs a character", 2),
        ("a b", "not a token or a quoted-string", 1),
        ("", "not a token or a quoted-string", 0),
        (" a", "not a token or a quoted-string", 0),
    ],
)
def test_strict_unquote_rejects_malformed_values(value: str, reason: str, offset: int) -> None:
    with pytest.raises(QuotedStringError) as caught:
        unquote(value, strict=True)
    assert (caught.value.reason, caught.value.offset) == (reason, offset)
    assert str(caught.value) == f"{reason} at offset {offset}"


@pytest.mark.parametrize(
    "value",
    ['a"b', "a\\b", "", 'path "with" spaces', "trailing backslash\\", 'only"quote', "\t \u00ff"],
)
def test_quote_then_unquote_round_trips(value: str) -> None:
    assert unquote(quote(value)) == value
    assert unquote(quote(value), strict=True) == value
