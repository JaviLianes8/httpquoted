import pytest

from httpquoted import QuotedStringError, quote_comment, unquote_comment


def test_quote_comment_wraps_a_value_in_parentheses() -> None:
    assert quote_comment("Windows NT 10.0; Win64") == "(Windows NT 10.0; Win64)"


def test_quote_comment_escapes_parentheses_and_backslash_only() -> None:
    assert quote_comment('a(b)c\\"d') == '(a\\(b\\)c\\\\"d)'


def test_quote_comment_refuses_controls_and_honours_ascii_only() -> None:
    with pytest.raises(QuotedStringError, match=r"U\+000A is not allowed at offset 1"):
        quote_comment("a\nb")
    with pytest.raises(QuotedStringError, match="obs-text"):
        quote_comment("\u00e9", ascii_only=True)
    assert quote_comment("\u00e9") == "(\u00e9)"


def test_unquote_comment_resolves_quoted_pairs_and_keeps_nesting() -> None:
    assert unquote_comment("(a (b) \\) c)") == "a (b) ) c"
    assert unquote_comment("(a (b) \\) c)", strict=True) == "a (b) ) c"


def test_unquote_comment_returns_a_value_without_parentheses_unchanged() -> None:
    assert unquote_comment("abc") == "abc"
    assert unquote_comment("(abc") == "(abc"


@pytest.mark.parametrize(
    ("value", "reason", "offset"),
    [
        ("(a) b", "text after the closing parenthesis", 3),
        ("(a", "unterminated comment", 0),
        ("a", "a comment must start with (", 0),
        ("", "a comment must start with (", 0),
        ("(a\x00)", "U+0000 is not allowed in a comment", 2),
    ],
)
def test_strict_unquote_comment_rejects_malformed_values(
    value: str, reason: str, offset: int
) -> None:
    with pytest.raises(QuotedStringError) as caught:
        unquote_comment(value, strict=True)
    assert (caught.value.reason, caught.value.offset) == (reason, offset)


@pytest.mark.parametrize("value", ["", "a(b", ")(", "\\", "((x))", 'say "hi"', "\t\u00ff"])
def test_quote_comment_then_unquote_comment_round_trips(value: str) -> None:
    assert unquote_comment(quote_comment(value)) == value
    assert unquote_comment(quote_comment(value), strict=True) == value
