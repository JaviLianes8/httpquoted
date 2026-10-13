from __future__ import annotations

import io
from collections.abc import Callable

import pytest

from httpquoted._cli import main

Run = Callable[..., tuple[int, str, str]]


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> Run:
    """Call the entry point with arguments and standard input; return status, out, err."""

    def call(*args: str, stdin: str = "") -> tuple[int, str, str]:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
        status = main(list(args))
        captured = capsys.readouterr()
        return status, captured.out, captured.err

    return call


def test_quote_prints_each_argument_quoted(run: Run) -> None:
    assert run("quote", 'a"b', "c") == (0, '"a\\"b"\n"c"\n', "")


def test_quote_comment_and_ascii_only(run: Run) -> None:
    assert run("quote", "--comment", "a(b")[1] == "(a\\(b)\n"
    status, out, err = run("quote", "--ascii-only", "\u00e9")
    assert (status, out) == (1, "")
    assert err == "httpquoted: U+00E9 is obs-text at offset 0\n"


def test_unquote_reads_values_from_standard_input(run: Run) -> None:
    result = run("unquote", stdin='"a\\"b"\r\ntoken\n')
    assert result == (0, 'a"b\ntoken\n', "")


def test_unquote_strict_exits_one_with_the_reason(run: Run) -> None:
    assert run("unquote", '"a"b"') == (0, 'a"b\n', "")
    status, out, err = run("unquote", "--strict", '"a"b"')
    assert (status, out) == (1, "")
    assert err == "httpquoted: text after the closing quote at offset 3\n"


def test_unquote_comment(run: Run) -> None:
    assert run("unquote", "--comment", "--strict", "(a (b))")[1] == "a (b)\n"


def test_split_prints_one_element_per_line(run: Run) -> None:
    out = run("split", 'gzip, "a,b", br')[1]
    assert out == 'gzip\n"a,b"\nbr\n'


def test_split_options(run: Run) -> None:
    out = run("split", "--separator", ";", "a;b")[1]
    assert out == "a\nb\n"
    out = run("split", "--comments", "1.0 a (x, y), 1.1 b")[1]
    assert out == "1.0 a (x, y)\n1.1 b\n"
    status, _, err = run("split", "--strict", 'a, "b')
    assert status == 1
    assert "unterminated quoted-string" in err


def test_a_bad_separator_is_a_usage_error(run: Run, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        run("split", "--separator", ";;", "a")
    assert caught.value.code == 2
    assert "separator must be one field character" in capsys.readouterr().err


def test_a_command_is_required(run: Run) -> None:
    with pytest.raises(SystemExit) as caught:
        run()
    assert caught.value.code == 2
