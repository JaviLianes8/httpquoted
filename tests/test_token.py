import pytest

from httpquoted import is_token


@pytest.mark.parametrize("value", ["gzip", "max-age", "X-Custom_Header", "a1", "!#$%&'*+-.^_`|~"])
def test_is_token_accepts_valid_tokens(value: str) -> None:
    assert is_token(value) is True


@pytest.mark.parametrize("value", ["", "a b", "a,b", 'a"b', "a/b", "a@b", "a\tb", "(comment)"])
def test_is_token_rejects_non_tokens(value: str) -> None:
    assert is_token(value) is False
