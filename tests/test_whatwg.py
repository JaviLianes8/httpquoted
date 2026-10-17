"""The lenient readers against the WHATWG Fetch Standard, as fetched.

The standard's source is read from tests/upstream (URL, revision and sha256 in
MANIFEST.json); those tests skip until `python scripts/fetch_upstream.py` has fetched it.
The seeded comparisons with the hand transcription in whatwg_reference.py always run.
"""

from __future__ import annotations

import html
import random
import re

import pytest
from conftest import read_upstream
from whatwg_reference import collect_http_quoted_string, get_decode_split

import httpquoted as hq

ALPHABET = [*'ab ,;"\\\t()=', "\xe9", "\x7f", "\x00", "\n", "\u20ac"]


@pytest.fixture(scope="module")
def fetch() -> str:
    return read_upstream("whatwg-fetch.bs.txt")


def _plain(cell: str) -> str:
    """A table cell without markup and without the outer quotes the standard writes."""
    text = html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()
    assert text.startswith('"') and text.endswith('"'), cell
    return text[1:-1]


def test_the_transcribed_steps_are_the_ones_in_the_standard(fetch: str) -> None:
    text = " ".join(re.sub(r"<[^>]+>", "", fetch).split())
    for step in (
        'that are not U+0022 (") or U+005C (\\) from input, given position, to value.',
        "If position is past the end of input, then append U+005C (\\) to value and break.",
        "Append the code point at position within input to value.",
        "If extract-value is true, then return value.",
        'that are not U+0022 (") or U+002C (,) from input, given position, to temporaryValue.',
        "If position is not past the end of input, then continue.",
        "Remove all HTTP tab or space from the start and end of temporaryValue.",
        "Append temporaryValue to values.",
    ):
        assert step in text, step


def test_the_quoted_string_examples_of_the_standard(fetch: str) -> None:
    table = fetch.split("id=example-http-quoted-string>", 1)[1].split("</table>", 1)[0]
    rows = [re.findall(r"<td>(.*)", row) for row in table.split("<tr>")[2:]]
    assert len(rows) == 3
    for source, raw, value, end in rows:
        text, expected_end = _plain(source), int(end)
        assert collect_http_quoted_string(text, 0, True) == (_plain(value), expected_end)
        assert collect_http_quoted_string(text, 0, False) == (_plain(raw), expected_end)
        assert hq.scan_quoted_string(text) == (_plain(value), expected_end)
        assert hq.scan_quoted_string(text.encode("latin-1")) == (
            _plain(value).encode("latin-1"),
            expected_end,
        )


def test_the_split_examples_of_the_standard(fetch: str) -> None:
    table = fetch.split("id=example-header-list-get-decode-split>", 1)[1].split("</table>", 1)[0]
    checked = []
    expected: list[str] = []
    for row in table.split("<tr>")[2:]:
        output = re.search("\u00ab(.*)\u00bb", row)
        if output is not None:  # rows without an output cell share the one above
            found = re.findall(r'"(?:<code>(.*?)</code>)?"', output.group(1))
            expected = [html.unescape(value) for value in found]
        lines = re.findall(r"^ *A:(.*)$", html.unescape(re.sub(r"<[^>]+>", "", row)), re.M)
        if not lines:  # the example without an A header returns null
            continue
        value = ", ".join(line.strip(" 	") for line in lines)
        assert get_decode_split(value) == expected, value
        assert hq.split_list(value) == [v for v in expected if v], value
        checked.append(value)
    assert checked == [
        "nosniff,",
        "nosniff, ",
        "",
        'text/html;", x/x',
        'text/html;", x/x',
        'x/x;test="hi",y/y',
        'x/x;test="hi", y/y',
        "x / x,,,1",
        "x / x, ,, 1",
        '"1,2", 3',
        '"1,2", 3',
    ]


@pytest.mark.parametrize("seed", range(4))
def test_scan_quoted_string_is_the_standard_algorithm(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(3000):
        text = '"' + "".join(rng.choice(ALPHABET) for _ in range(rng.randrange(12)))
        start = rng.randrange(3)
        text = "x" * start + text
        expected = collect_http_quoted_string(text, start, True)
        assert hq.scan_quoted_string(text, start) == expected, text
        octets = text.replace("\u20ac", "\xa4").encode("latin-1")
        value, end = collect_http_quoted_string(octets.decode("latin-1"), start, True)
        assert hq.scan_quoted_string(octets, start) == (value.encode("latin-1"), end)


@pytest.mark.parametrize("seed", range(4))
def test_split_list_is_the_standard_split_without_empty_values(seed: int) -> None:
    rng = random.Random(100 + seed)
    for _ in range(3000):
        text = "".join(rng.choice(ALPHABET) for _ in range(rng.randrange(16)))
        expected = [v for v in get_decode_split(text) if v]
        assert hq.split_list(text) == expected, text
        octets = text.replace("\u20ac", "\xa4").encode("latin-1")
        assert hq.split_list(octets) == [
            v.encode("latin-1") for v in get_decode_split(octets.decode("latin-1")) if v
        ]
