"""Header examples and test vectors read from fetched specifications and test suites.

Every value comes from a file in tests/upstream (URL, revision and sha256 in
MANIFEST.json); these tests skip until `python scripts/fetch_upstream.py` has fetched it.
"""

from __future__ import annotations

import ast
import re

import pytest
from conftest import read_upstream, rfc

import httpquoted as hq


def _field(text: str, name: str, index: int = 0) -> str:
    """The value of the index-th example field, its continuation lines folded in."""
    found = re.findall(rf"^ +{name}: (.*(?:\n {{6,}}\S.*)*)", text, re.M)
    return " ".join(found[index].split())


def _parameters(element: str, separator: str = ";") -> dict[str, str]:
    """Parameter names (lower-cased) and their unquoted values, read strictly."""
    found = {}
    for item in hq.split_list(element, separator=separator, strict=True):
        name, equals, value = item.partition("=")
        if equals:
            found[name.strip().lower()] = hq.unquote(value.strip(" \t"), strict=True)
    return found


def test_the_challenge_example_of_rfc_9110_section_11_6_1() -> None:
    value = _field(rfc(9110), "WWW-Authenticate")
    assert value.endswith(r'title="Login to \"apps\""')
    elements = hq.split_list(value, strict=True)
    assert elements[:2] == ['Basic realm="simple"', 'Newauth realm="apps"']
    assert _parameters(", ".join(elements[2:]), ",") == {"type": "1", "title": 'Login to "apps"'}


def test_the_community_directive_of_rfc_9111() -> None:
    (value,) = re.findall(r"^ +Cache-Control: (.*community.*)$", rfc(9111), re.M)
    assert value == 'private, community="UCI"'
    assert [hq.unquote(e.partition("=")[2] or e, strict=True) for e in hq.split_list(value)] == [
        "private",
        "UCI",
    ]


def test_the_digest_challenges_of_rfc_7616_keep_a_comma_inside_quotes() -> None:
    text = rfc(7616)
    for index in range(3):
        value = _field(text, "WWW-Authenticate", index).removeprefix("Digest ")
        found = _parameters(value, ",")
        assert found["realm"].endswith("example.org")
        assert found["qop"] in ("auth, auth-int", "auth")
        assert hq.split_list(found["qop"]) == ["auth", "auth-int"][: found["qop"].count(",") + 1]
        assert len(found["nonce"]) == 44 and found["opaque"] == found["opaque"].strip()


def test_the_content_disposition_examples_of_rfc_6266() -> None:
    text = rfc(6266)
    forms = [_field(text, "Content-Disposition", i) for i in range(4)]
    assert [_parameters(form).get("filename") for form in forms] == [
        "example.html",
        "an example.html",
        None,
        "EURO rates",
    ]
    assert hq.is_token("example.html") and hq.needs_quoting("an example.html")


def _literal(source: str, anchor: str) -> object:
    """The first Python list literal that follows `anchor` in a fetched test file."""
    start = source.index("[", source.index(anchor))
    end = start
    while True:
        end = source.index("]", end + 1)
        try:
            return ast.literal_eval(source[start : end + 1])
        except SyntaxError:
            continue


def _drop_pairs(element: str) -> str:
    """Remove the backslash of every quoted-pair inside the quoted-strings of an element."""
    out, pos = [], 0
    while (start := element.find('"', pos)) != -1:
        value, end = hq.scan_quoted_string(element, start)
        closed = hq.scan_quoted_string(element[start:end] + "x")[1] == end - start
        out.append(element[pos:start] + '"' + value + ('"' if closed else ""))
        pos = end
    return "".join(out) + element[pos:]


def test_the_parse_http_list_vectors_of_cpython() -> None:
    source = read_upstream("cpython-test_urllib2.py.txt")
    vectors = _literal(source.split("def test_parse_http_list", 1)[1], "tests =")
    assert isinstance(vectors, list) and len(vectors) == 4
    for value, expected in vectors:
        assert [_drop_pairs(e) for e in hq.split_list(value)] == expected, value


def test_the_list_header_vectors_of_werkzeug() -> None:
    source = read_upstream("werkzeug-test_http.py.txt").split("def test_list_header", 1)[0]
    block = source.rsplit("@pytest.mark.parametrize(", 1)[1]
    vectors = _literal(block, '("value", "expect"),')
    assert isinstance(vectors, list) and len(vectors) == 7
    for value, expected in vectors:
        if expected == []:  # Werkzeug drops a list whose quoted-string never closes
            with pytest.raises(hq.QuotedStringError, match="unterminated"):
                hq.split_list(value, strict=True)
            continue
        assert [hq.unquote(e) for e in hq.split_list(value, strict=True)] == expected, value
