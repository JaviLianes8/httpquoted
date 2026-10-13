import pytest

from httpquoted import is_token


@pytest.mark.parametrize("value", ["gzip", "max-age", "X-Custom_Header", "a1", "!#$%&'*+-.^_`|~"])
def test_is_token_accepts_valid_tokens(value: str) -> None:
    assert is_token(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        "a b",
        "a,b",
        'a"b',
        "a/b",
        "a@b",
        "a\tb",
        "(comment)",
        "a\n",
        "\u00e9",
        "\uff21",
        "\u0661",
    ],
)
def test_is_token_rejects_non_tokens(value: str) -> None:
    assert is_token(value) is False


def test_is_token_matches_tchar_over_the_whole_latin_1_range() -> None:
    delimiters = set('"(),/:;<=>?@[\\]{}')
    expected = {chr(c) for c in range(0x21, 0x7F)} - delimiters
    assert {chr(c) for c in range(0x100) if is_token(chr(c))} == expected
