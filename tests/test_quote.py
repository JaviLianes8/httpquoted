import pytest

from httpquoted import quote, unquote


def test_quote_wraps_a_plain_value_in_double_quotes() -> None:
    assert quote("gzip") == '"gzip"'


def test_quote_escapes_an_embedded_double_quote() -> None:
    assert quote('a"b') == '"a\\"b"'


def test_quote_escapes_a_backslash() -> None:
    assert quote("a\\b") == '"a\\\\b"'


def test_quote_handles_the_empty_value() -> None:
    assert quote("") == '""'


def test_unquote_strips_the_surrounding_quotes() -> None:
    assert unquote('"gzip"') == "gzip"


def test_unquote_resolves_an_escaped_double_quote() -> None:
    assert unquote('"a\\"b"') == 'a"b'


def test_unquote_returns_a_bare_token_unchanged() -> None:
    assert unquote("gzip") == "gzip"


def test_unquote_handles_the_empty_quoted_string() -> None:
    assert unquote('""') == ""


@pytest.mark.parametrize(
    "value",
    ['a"b', "a\\b", "", 'path "with" spaces', "trailing backslash\\", 'only"quote'],
)
def test_quote_then_unquote_round_trips(value: str) -> None:
    assert unquote(quote(value)) == value
