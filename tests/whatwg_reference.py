"""Hand transcription of two WHATWG Fetch algorithms, used as an independent reference.

Transcribed by hand, step by step, from the Fetch Standard source at
https://raw.githubusercontent.com/whatwg/fetch/e9460d1b22ead1c6a72eeac37fb2ec0dc01aeb1d/fetch.bs
("collect an HTTP quoted string" and "get, decode, and split" for a header value). This
is not a copy of the standard: tests/test_whatwg.py checks that the step sentences these
lines follow are present in the fetched text and runs the standard's own example tables.
"""

from __future__ import annotations


def collect_http_quoted_string(text: str, position: int, extract_value: bool) -> tuple[str, int]:
    """The quoted string at `position` (raw, or its value) and the position after it."""
    start = position
    value: list[str] = []
    assert text[position] == '"'
    position += 1
    while True:
        run = position
        while run < len(text) and text[run] not in '"\\':
            run += 1
        value.append(text[position:run])
        position = run
        if position >= len(text):
            break
        quote_or_backslash = text[position]
        position += 1
        if quote_or_backslash == "\\":
            if position >= len(text):
                value.append("\\")
                break
            value.append(text[position])
            position += 1
        else:
            assert quote_or_backslash == '"'
            break
    if extract_value:
        return "".join(value), position
    return text[start:position], position


def get_decode_split(text: str) -> list[str]:
    """Split a header value on commas outside quoted strings, keeping empty values."""
    position = 0
    values: list[str] = []
    temporary = ""
    while True:
        run = position
        while run < len(text) and text[run] not in '",':
            run += 1
        temporary += text[position:run]
        position = run
        if position < len(text) and text[position] == '"':
            collected, position = collect_http_quoted_string(text, position, False)
            temporary += collected
            if position < len(text):
                continue
        values.append(temporary.strip("\t "))
        temporary = ""
        if position >= len(text):
            return values
        assert text[position] == ","
        position += 1
