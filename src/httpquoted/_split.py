"""Split a comma-separated header value while respecting quoted-strings."""

from __future__ import annotations


def split_list(header: str) -> list[str]:
    """Split a list-style header on commas that sit outside a quoted-string.

    A comma inside double quotes is part of the value, not a separator, and a
    quoted-pair never ends the quotes. Each element is trimmed of surrounding
    optional whitespace, and empty elements are dropped per the list rule.
    """
    elements: list[str] = []
    current: list[str] = []
    in_quotes = False
    escaped = False
    for char in header:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\" and in_quotes:
            current.append(char)
            escaped = True
        elif char == '"':
            current.append(char)
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            _flush(current, elements)
            current = []
        else:
            current.append(char)
    _flush(current, elements)
    return elements


def _flush(current: list[str], elements: list[str]) -> None:
    element = "".join(current).strip(" \t")
    if element:
        elements.append(element)
