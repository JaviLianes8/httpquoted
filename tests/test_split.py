from httpquoted import split_list


def test_split_list_separates_plain_elements() -> None:
    assert split_list("gzip, deflate, br") == ["gzip", "deflate", "br"]


def test_split_list_keeps_a_comma_inside_quotes() -> None:
    assert split_list('"a,b", c') == ['"a,b"', "c"]


def test_split_list_keeps_an_escaped_quote_inside_quotes() -> None:
    assert split_list('"a\\"b", c') == ['"a\\"b"', "c"]


def test_split_list_trims_surrounding_whitespace() -> None:
    assert split_list("  gzip  ,\tdeflate\t") == ["gzip", "deflate"]


def test_split_list_drops_empty_elements() -> None:
    assert split_list("gzip,,deflate,") == ["gzip", "deflate"]


def test_split_list_returns_empty_for_a_blank_header() -> None:
    assert split_list("") == []
    assert split_list("  ,  ") == []


def test_split_list_preserves_whitespace_inside_quotes() -> None:
    assert split_list('"a, b" , c') == ['"a, b"', "c"]
