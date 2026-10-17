"""The command line contract: exit statuses, octets in and out, no tracebacks."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from httpquoted import _cli
from httpquoted._cli import main

SRC = str(Path(__file__).resolve().parents[1] / "src")


def _run(*args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    code = f"import sys; sys.path.insert(0, {SRC!r}); from httpquoted._cli import main; "
    code += "sys.exit(main())"
    return subprocess.run(
        [sys.executable, "-c", code, *args], input=stdin, capture_output=True, check=False
    )


@pytest.mark.parametrize(
    ("args", "status"),
    [
        (["quote", "a b"], 0),
        (["quote", "a\x01b"], 1),
        (["unquote", "--strict", '"a'], 1),
        (["split", "--strict", "a, (b", "--comments"], 1),
        ([], 2),
        (["nope"], 2),
        (["quote", "--strict", "a"], 2),
        (["split", "--separator", '"', "a"], 2),
        (["split", "--separator", ";;", "a"], 2),
    ],
)
def test_exit_statuses_in_a_real_process(args: list[str], status: int) -> None:
    result = _run(*args)
    assert result.returncode == status, result.stderr
    assert b"Traceback" not in result.stderr
    if status == 1:
        assert result.stderr.startswith(b"httpquoted: ") and result.stdout == b""


def test_standard_input_is_read_and_written_as_octets_in_a_real_process() -> None:
    result = _run("unquote", stdin=b'"caf\xc3\xa9 \\"x\\""\r\n"\xff"\n')
    assert (result.returncode, result.stdout) == (0, b'caf\xc3\xa9 "x"\n\xff\n')


def test_an_interrupt_exits_130_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupted() -> list[str]:
        raise KeyboardInterrupt

    monkeypatch.setattr(_cli, "_read_lines", interrupted)
    assert main(["quote"]) == 130
    assert capsys.readouterr().err == ""


class _ClosedPipe(io.StringIO):
    def write(self, text: str) -> int:
        raise BrokenPipeError

    def flush(self) -> None:
        raise BrokenPipeError


def test_a_closed_output_exits_1_quietly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", _ClosedPipe())
    assert main(["quote", "a", "b"]) == 1
    assert capsys.readouterr().err == ""


def _posix_command_line(
    monkeypatch: pytest.MonkeyPatch, platform: str, *args: str
) -> tuple[int, bytes]:
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(sys, "argv", ["httpquoted", *args])
    monkeypatch.setattr(sys, "stdout", out)
    status = main()
    out.flush()
    buffer = out.buffer
    assert isinstance(buffer, io.BytesIO)
    return status, buffer.getvalue()


def test_posix_arguments_are_read_back_as_their_octets(monkeypatch: pytest.MonkeyPatch) -> None:
    # The file system codec turned the octets of "caf\xc3\xa9" into "caf\xe9"; recover them.
    status, out = _posix_command_line(monkeypatch, "linux", "quote", "caf\xe9")
    assert (status, out) == (0, b'"caf\xc3\xa9"\n')
    status, out = _posix_command_line(monkeypatch, "linux", "split", "--separator", "|", "a|b")
    assert (status, out) == (0, b"a\nb\n")


def test_windows_arguments_are_text_written_as_iso_8859_1(monkeypatch: pytest.MonkeyPatch) -> None:
    status, out = _posix_command_line(monkeypatch, "win32", "quote", "caf\xe9")
    assert (status, out) == (0, b'"caf\xe9"\n')


def test_arguments_passed_to_main_are_used_as_given(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "stdout", out)
    assert main(["quote", "caf\xe9"]) == 0
    out.flush()
    buffer = out.buffer
    assert isinstance(buffer, io.BytesIO)
    assert buffer.getvalue() == b'"caf\xe9"\n'


def test_a_reader_that_closes_early_gets_exit_1_without_a_traceback(tmp_path: Path) -> None:
    source = tmp_path / "big.txt"
    source.write_bytes(b"a," * 400_000 + b"\n")
    code = f"import sys; sys.path.insert(0, {SRC!r}); from httpquoted._cli import main; "
    code += "sys.exit(main())"
    with source.open("rb") as stdin:
        process = subprocess.Popen(
            [sys.executable, "-c", code, "split"],
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None and process.stderr is not None
        assert process.stdout.readline() == b"a\n"
        process.stdout.close()
        error = process.stderr.read()
        assert process.wait(timeout=60) == 1
        process.stderr.close()
    assert error == b""


def test_other_os_errors_are_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> list[str]:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(_cli, "_read_lines", broken)
    with pytest.raises(PermissionError):
        main(["quote"])
