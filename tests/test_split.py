import pytest

from httpquoted import QuotedStringError, split_list


def test_split_list_separates_plain_elements() -> None:
    assert split_list("gzip, deflate, br") == ["gzip", "deflate", "br"]


def test_split_list_keeps_a_comma_inside_quotes() -> None:
    assert split_list('"a,b", c') == ['"a,b"', "c"]


def test_split_list_keeps_an_escaped_quote_inside_quotes() -> None:
    assert split_list('"a\\"b", c') == ['"a\\"b"', "c"]


def test_split_list_keeps_an_escaped_backslash_before_the_closing_quote() -> None:
    assert split_list('"a\\\\", b') == ['"a\\\\"', "b"]


def test_split_list_trims_surrounding_whitespace() -> None:
    assert split_list("  gzip  ,\tdeflate\t") == ["gzip", "deflate"]


def test_split_list_drops_empty_elements() -> None:
    assert split_list("gzip,,deflate,") == ["gzip", "deflate"]


def test_split_list_returns_empty_for_a_blank_header() -> None:
    assert split_list("") == []
    assert split_list("  ,  ") == []


def test_split_list_preserves_whitespace_inside_quotes() -> None:
    assert split_list('"a, b" , c') == ['"a, b"', "c"]


def test_split_list_ignores_parentheses_unless_asked() -> None:
    assert split_list("1.0 fred (a, b), 1.1 x") == ["1.0 fred (a", "b)", "1.1 x"]


def test_split_list_skips_comments_as_a_unit_when_asked() -> None:
    value = '1.0 fred (a, (b, c) "d,), 1.1 p.example.net'
    assert split_list(value, comments=True) == ['1.0 fred (a, (b, c) "d,)', "1.1 p.example.net"]


def test_split_list_with_comments_still_respects_quotes() -> None:
    assert split_list('"(", x', comments=True) == ['"("', "x"]


def test_split_list_lenient_ignores_a_stray_closing_parenthesis() -> None:
    assert split_list("a), b", comments=True) == ["a)", "b"]


def test_split_list_splits_parameters_on_semicolons() -> None:
    value = 'text/plain; charset="a;b"; format=flowed'
    assert split_list(value, separator=";") == ["text/plain", 'charset="a;b"', "format=flowed"]


def test_split_list_does_not_split_on_commas_when_the_separator_is_a_semicolon() -> None:
    assert split_list("a, b; c", separator=";") == ["a, b", "c"]


@pytest.mark.parametrize("separator", ["", ";;", '"', "\\", "(", ")"])
def test_split_list_rejects_a_separator_that_cannot_work(separator: str) -> None:
    with pytest.raises(ValueError, match="separator"):
        split_list("a", separator=separator)


@pytest.mark.parametrize("separator", ["]", "^", "-", "."])
def test_split_list_takes_regex_metacharacters_literally(separator: str) -> None:
    assert split_list(f"a{separator}b", separator=separator) == ["a", "b"]
    quoted = f'"x{separator}y"'
    assert split_list(f"{quoted}{separator}c", separator=separator) == [quoted, "c"]


def test_lenient_split_returns_an_unterminated_quoted_string_as_an_element() -> None:
    assert split_list('a, "b, c') == ["a", '"b, c']
    assert split_list("a, (b, c", comments=True) == ["a", "(b, c"]


@pytest.mark.parametrize(
    ("value", "comments", "reason", "offset"),
    [
        ('a, "b, c', False, "unterminated quoted-string", 3),
        ("a, (b, c", True, "unterminated comment", 3),
        ("a), b", True, "unbalanced )", 1),
        ("a,\r\n b", False, "U+000D is not allowed", 2),
        ("a, b\x00", False, "U+0000 is not allowed", 4),
        ('"a\\\x01"', False, "U+0001 is not allowed", 3),
    ],
)
def test_strict_split_rejects_malformed_lists(
    value: str, comments: bool, reason: str, offset: int
) -> None:
    with pytest.raises(QuotedStringError) as caught:
        split_list(value, comments=comments, strict=True)
    assert (caught.value.reason, caught.value.offset) == (reason, offset)


def test_strict_split_accepts_well_formed_lists() -> None:
    value = 'W/"x", "a,b" , (c, "d) e, \u00e9'
    assert split_list(value, comments=True, strict=True) == [
        'W/"x"',
        '"a,b"',
        '(c, "d) e',
        "\u00e9",
    ]
