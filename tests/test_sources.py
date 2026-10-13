"""Check the library against RFC 9110, RFC 7230 and RFC 5234 as fetched.

The character sets are evaluated from the ABNF in the fetched text and compared with what
the functions accept, character by character. The files are read from tests/upstream
(URL, size and sha256 in MANIFEST.json); these tests skip until
`python scripts/fetch_upstream.py` has fetched them.
"""

from __future__ import annotations

import re

import pytest
from conftest import rule, section

import httpquoted as hq

PROBE = [chr(c) for c in range(0x110)] + ["\u20ac", "\uffff"]
TERM = re.compile(r'%x([0-9A-Fa-f]+)(?:-([0-9A-Fa-f]+))?|"([^"]*)"|([A-Za-z][\w-]*)')


def charset(expression: str, sources: list[str]) -> set[str]:
    """Evaluate an ABNF alternation of single characters, resolving rule names in sources."""
    found: set[str] = set()
    for low, high, literal, name in TERM.findall(expression):
        if low:
            found |= {chr(c) for c in range(int(low, 16), int(high or low, 16) + 1)}
        elif literal:
            assert len(literal) == 1, literal
            found.add(literal)
        else:
            text = next(s for s in sources if re.search(rf"^ +{name} +=", s, re.M))
            found |= charset(rule(text, name), sources)
    return found


@pytest.fixture(scope="module")
def grammar(rfc9110: str, rfc5234: str) -> dict[str, set[str]]:
    sources = [rfc9110, rfc5234]
    pair = rule(rfc9110, "quoted-pair").strip()
    assert pair.startswith('"\\"')
    return {
        "qdtext": charset(rule(rfc9110, "qdtext"), sources),
        "ctext": charset(rule(rfc9110, "ctext"), sources),
        "tchar": charset(rule(rfc9110, "tchar"), sources),
        "obs-text": charset(rule(rfc9110, "obs-text"), sources),
        "quoted-pair": charset(pair[3:], sources),
    }


def test_the_shapes_of_quoted_string_and_comment(rfc9110: str) -> None:
    assert " ".join(rule(rfc9110, "quoted-string").split()) == (
        "DQUOTE *( qdtext / quoted-pair ) DQUOTE"
    )
    assert (
        " ".join(rule(rfc9110, "comment").split()) == '"(" *( ctext / quoted-pair / comment ) ")"'
    )


def test_qdtext_is_what_a_strict_quoted_string_accepts(grammar: dict[str, set[str]]) -> None:
    accepted = set()
    for char in PROBE:
        try:
            if hq.scan_quoted_string(f'"{char}"', strict=True)[1] == 3:
                accepted.add(char)
        except hq.QuotedStringError:
            pass
    assert accepted == grammar["qdtext"]


def test_ctext_is_what_a_strict_comment_accepts(grammar: dict[str, set[str]]) -> None:
    accepted = set()
    for char in PROBE:
        try:
            if hq.scan_comment(f"({char})", strict=True)[1] == 3:
                accepted.add(char)
        except hq.QuotedStringError:
            pass
    assert accepted == grammar["ctext"]


def test_quoted_pair_is_what_both_scanners_accept(grammar: dict[str, set[str]]) -> None:
    for scan, opener, closer in ((hq.scan_quoted_string, '"', '"'), (hq.scan_comment, "(", ")")):
        accepted = set()
        for char in PROBE:
            try:
                if scan(f"{opener}\\{char}{closer}", strict=True) == (char, 4):
                    accepted.add(char)
            except hq.QuotedStringError:
                pass
        assert accepted == grammar["quoted-pair"]


def test_quote_accepts_exactly_what_quoted_pair_can_carry(grammar: dict[str, set[str]]) -> None:
    for encode in (hq.quote, hq.quote_comment):
        accepted = set()
        ascii_only = set()
        for char in PROBE:
            try:
                encode(char)
                accepted.add(char)
                encode(char, ascii_only=True)
                ascii_only.add(char)
            except hq.QuotedStringError:
                pass
        assert accepted == grammar["quoted-pair"]
        assert accepted - ascii_only == grammar["obs-text"]


def test_tchar_is_what_is_token_accepts(grammar: dict[str, set[str]]) -> None:
    assert {char for char in PROBE if hq.is_token(char)} == grammar["tchar"]


def test_delimiters_of_section_5_6_2_are_never_token_characters(rfc9110: str) -> None:
    match = re.search(r'\(DQUOTE and "([^"]+)"\)', section(rfc9110, "5.6.2.  Tokens", "5.6.3."))
    assert match is not None
    for char in '"' + match.group(1):
        assert hq.needs_quoting("a" + char)


def test_senders_escape_only_what_section_5_6_4_allows(rfc9110: str) -> None:
    text = " ".join(section(rfc9110, "5.6.4.  Quoted Strings", "5.6.5.").split())
    assert "except where necessary to quote DQUOTE and backslash octets" in text
    assert 'necessary to quote parentheses ["(" and ")"] and backslash octets' in text
    for char in (c for c in PROBE if c in "\t" or " " <= c <= "~" or "\x80" <= c <= "\xff"):
        assert ("\\" in hq.quote(char)) is (char in '"\\')
        assert ("\\" in hq.quote_comment(char)) is (char in "()\\")


def test_rfc_7230_has_the_same_grammar(rfc7230: str, rfc9110: str, rfc5234: str) -> None:
    # Erratum 4891 (held) only adds the missing space in "SP /%x21"; the set is the same.
    old = section(rfc7230, "3.2.6.  Field Value Components", "3.3.  ")
    for name in ("qdtext", "ctext", "tchar", "obs-text"):
        then = charset(rule(old, name), [rfc7230, rfc5234])
        assert then == charset(rule(rfc9110, name), [rfc9110, rfc5234]), name
    for name in ("quoted-string", "quoted-pair", "comment"):
        assert rule(old, name).split() == rule(rfc9110, name).split(), name


def test_the_list_examples_of_section_5_6_1_2(rfc9110: str) -> None:
    text = section(rfc9110, "5.6.1.2.  Recipient Requirements", "5.6.2.")
    valid, invalid = text.split("In contrast", 1)
    good = re.findall(r'^ {5}"(.*)"$', valid, re.M)
    bad = re.findall(r'^ {5}"(.*)"$', invalid, re.M)
    assert good == ["foo,bar", "foo ,bar,", "foo , ,bar,charlie"]
    assert [hq.split_list(v, strict=True) for v in good] == [
        ["foo", "bar"],
        ["foo", "bar"],
        ["foo", "bar", "charlie"],
    ]
    assert len(bad) == 3
    assert all(hq.split_list(v, strict=True) == [] for v in bad)


def test_the_equivalent_media_types_of_section_8_3_1(rfc9110: str) -> None:
    text = section(rfc9110, "8.3.1.  Media Type", "8.3.2.")
    forms = re.findall(r"^ {5}(\S.*charset.*)$", text, re.M | re.I)
    assert len(forms) == 4
    for form in forms:
        media, parameter = hq.split_list(form, separator=";", strict=True)
        name, value = parameter.split("=", 1)
        assert (media.lower(), name.lower()) == ("text/html", "charset")
        assert hq.unquote(value, strict=True).lower() == "utf-8"


def test_the_entity_tag_lists_of_section_13_1(rfc9110: str) -> None:
    text = section(rfc9110, "13.1.1.  If-Match", "13.1.3.")
    lines = re.findall(r"^ +If-(?:None-)?Match: (.+)$", text, re.M)
    assert len(lines) == 8
    for line in lines:
        for element in hq.split_list(line, strict=True):
            tag = element.removeprefix("W/")
            assert tag == "*" or hq.unquote(tag, strict=True) == tag.strip('"')
