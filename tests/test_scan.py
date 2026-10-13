import pytest

from httpquoted import QuotedStringError, scan_comment, scan_quoted_string


def test_scan_quoted_string_returns_the_value_and_the_offset_after_it() -> None:
    text = 'title="a \\"b\\" c"; next=1'
    value, end = scan_quoted_string(text, 6)
    assert value == 'a "b" c'
    assert text[end:] == "; next=1"


def test_scan_quoted_string_starts_at_offset_zero_by_default() -> None:
    assert scan_quoted_string('"x", y') == ("x", 3)


def test_scan_quoted_string_needs_an_opening_quote() -> None:
    with pytest.raises(QuotedStringError, match="must start with") as caught:
        scan_quoted_string('a="b"', 0)
    assert caught.value.offset == 0


@pytest.mark.parametrize("start", [-1, 3, 10])
def test_scan_quoted_string_refuses_a_start_outside_the_text(start: int) -> None:
    with pytest.raises(QuotedStringError):
        scan_quoted_string('"a"', start)


def test_lenient_scan_runs_an_unterminated_string_to_the_end() -> None:
    assert scan_quoted_string('"abc') == ("abc", 4)
    assert scan_quoted_string('"ab\\') == ("ab\\", 4)


def test_lenient_scan_accepts_controls_between_the_quotes() -> None:
    assert scan_quoted_string('"a\x01b"') == ("a\x01b", 5)


def test_strict_scan_accepts_every_qdtext_and_quoted_pair_character() -> None:
    inner = "".join(chr(c) for c in [9, *range(0x20, 0x7F), *range(0x80, 0x100)])
    escaped = inner.replace("\\", "\\\\").replace('"', '\\"')
    assert scan_quoted_string(f'"{escaped}"', strict=True) == (inner, len(escaped) + 2)
    pairs = "".join("\\" + char for char in inner)
    assert scan_quoted_string(f'"{pairs}"', strict=True)[0] == inner


@pytest.mark.parametrize(
    ("text", "reason", "offset"),
    [
        ('"abc', "unterminated quoted-string", 0),
        ('x "a\x00"', "U+0000 is not allowed in a quoted-string", 4),
        ('"\x7f"', "U+007F is not allowed in a quoted-string", 1),
        ('"\u0100"', "U+0100 is not allowed in a quoted-string", 1),
        ('"a\\\x00"', "U+0000 cannot be quoted", 3),
        ('"a\\', "a quoted-pair needs a character", 2),
    ],
)
def test_strict_scan_reports_the_broken_rule_and_offset(
    text: str, reason: str, offset: int
) -> None:
    start = text.index('"')
    with pytest.raises(QuotedStringError) as caught:
        scan_quoted_string(text, start, strict=True)
    assert (caught.value.reason, caught.value.offset) == (reason, offset)


def test_scan_comment_keeps_nested_comments_and_resolves_quoted_pairs() -> None:
    text = 'Mozilla/5.0 (X11; (nested \\) "x) y) rest'
    value, end = scan_comment(text, 12)
    assert value == 'X11; (nested ) "x) y'
    assert text[end:] == " rest"


def test_scan_comment_treats_a_double_quote_as_plain_text() -> None:
    assert scan_comment('(a "b) c', strict=True) == ('a "b', 6)


def test_scan_comment_needs_an_opening_parenthesis() -> None:
    with pytest.raises(QuotedStringError, match="a comment must start with"):
        scan_comment("a (b)", 0)


def test_lenient_scan_comment_runs_an_unbalanced_comment_to_the_end() -> None:
    assert scan_comment("(a (b)") == ("a (b)", 6)
    assert scan_comment("(a\\") == ("a\\", 3)


@pytest.mark.parametrize(
    ("text", "reason", "offset"),
    [
        ("(a (b)", "unterminated comment", 0),
        ("(a\r\n)", "U+000D is not allowed in a comment", 2),
        ("(a\\\x7f)", "U+007F cannot be quoted", 3),
        ("(a\\", "a quoted-pair needs a character", 2),
    ],
)
def test_strict_scan_comment_reports_the_broken_rule(text: str, reason: str, offset: int) -> None:
    with pytest.raises(QuotedStringError) as caught:
        scan_comment(text, strict=True)
    assert (caught.value.reason, caught.value.offset) == (reason, offset)


def test_scan_comment_nests_deeply_without_recursion() -> None:
    depth = 200_000
    text = "(" * depth + "x" + ")" * depth
    value, end = scan_comment(text, strict=True)
    assert end == len(text)
    assert value == text[1:-1]
