"""httpquoted against established HTTP parsers run on the same seeded inputs.

tests/fixtures/oracle_runs.json holds the answers of Werkzeug, h11, the standard library
and Node's `util.MIMEType`, recorded by scripts/oracle_fixture.py. Every comparison below
runs on those answers; when the same tool versions are installed they are run again live
and must give the same answers. Each known difference is named and checked, not skipped.
"""

from __future__ import annotations

import email.utils
import importlib.metadata
import json
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import httpquoted as hq

ROOT = Path(__file__).resolve().parents[1]
RUNS: dict[str, Any] = json.loads(
    (ROOT / "tests" / "fixtures" / "oracle_runs.json").read_text(encoding="utf-8")
)
CASES: dict[str, list[str]] = RUNS["cases"]
sys.path.insert(0, str(ROOT / "scripts"))
import oracle_fixture  # noqa: E402


def _unclosed(value: str) -> bool:
    try:
        hq.split_list(value, strict=True)
    except hq.QuotedStringError as error:
        return error.reason in ("unterminated quoted-string", "a quoted-pair needs a character")
    return False


def test_the_cases_are_the_seeded_ones() -> None:
    assert oracle_fixture.cases() == CASES
    assert sum(len(v) for v in CASES.values()) > 2000


def test_werkzeug_quote_header_value_is_quote_if_needed() -> None:
    for value, answer in zip(CASES["quote"], RUNS["werkzeug_quote"], strict=True):
        assert hq.quote_if_needed(value) == answer, value


def test_werkzeug_unquote_header_value_is_lenient_unquote() -> None:
    for value, answer in zip(CASES["unquote"], RUNS["werkzeug_unquote"], strict=True):
        assert hq.unquote(value) == answer, value


def test_werkzeug_parse_list_header_is_split_then_unquote() -> None:
    # Werkzeug gives up on the whole list when a quoted-string never closes; httpquoted
    # keeps the tail lenient and raises in strict mode.
    unclosed = 0
    for value, answer in zip(CASES["list"], RUNS["werkzeug_list"], strict=True):
        if _unclosed(value):
            assert answer == [], value
            unclosed += 1
            continue
        assert [hq.unquote(item) for item in hq.split_list(value)] == answer, value
    assert 50 < unclosed < len(CASES["list"]) - 300


@pytest.mark.parametrize("live", [False, True], ids=["recorded", "live"])
def test_urllib_parse_http_list_splits_at_the_same_commas(live: bool) -> None:
    # parse_http_list keeps empty items and drops the backslash of a quoted-pair; compare
    # the non-empty items with every backslash removed on both sides.
    answers = (
        [urllib.request.parse_http_list(v) for v in CASES["list"]] if live else RUNS["urllib_list"]
    )
    for value, answer in zip(CASES["list"], answers, strict=True):
        ours = [item.replace("\\", "") for item in hq.split_list(value)]
        assert ours == [item.replace("\\", "") for item in answer if item], value


@pytest.mark.parametrize("live", [False, True], ids=["recorded", "live"])
def test_email_utils_quote_and_unquote_agree(live: bool) -> None:
    answers = [email.utils.quote(v) for v in CASES["quote"]] if live else RUNS["email_quote"]
    for value, answer in zip(CASES["quote"], answers, strict=True):
        assert hq.quote(value) == f'"{answer}"', value
        assert email.utils.unquote(hq.quote(value)) == value, value


def test_h11_token_is_is_token() -> None:
    assert [hq.is_token(bytes([b])) for b in range(256)] == RUNS["h11_token"]


def test_h11_field_content_differs_only_on_controls_rfc_9110_refuses() -> None:
    def accepted(octet: bytes) -> bool:
        try:
            hq.quote(octet)
        except hq.QuotedStringError:
            return False
        return True

    differ = {b for b in range(256) if accepted(bytes([b])) != RUNS["h11_field"][b]}
    assert differ == {*range(0x01, 0x09), *range(0x0E, 0x20), 0x7F}
    assert not any(accepted(bytes([b])) for b in differ)


def test_node_mime_type_parameters_read_the_scanned_value() -> None:
    answers = RUNS["node_mime"]
    assert answers is not None and len(answers) == len(CASES["mime"]) > 300
    for quoted, answer in zip(CASES["mime"], answers, strict=True):
        assert hq.scan_quoted_string(quoted)[0] == answer, quoted


def _installed(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def test_werkzeug_and_h11_answer_the_same_live() -> None:
    tools = RUNS["tools"]
    if (_installed("werkzeug"), _installed("h11")) != (tools["werkzeug"], tools["h11"]):
        pytest.skip(f"needs werkzeug {tools['werkzeug']} and h11 {tools['h11']}")
    live = oracle_fixture.python_oracles(CASES)
    assert live == {key: RUNS[key] for key in live}


def test_node_answers_the_same_live() -> None:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    assert oracle_fixture.node_oracle(CASES) == RUNS["node_mime"]
