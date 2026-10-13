"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with HTTPQUOTED_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("HTTPQUOTED_E2E") != "1", reason="set HTTPQUOTED_E2E=1 to build"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources
import httpquoted as hq

assert "site-packages" in hq.__file__, hq.__file__
assert importlib.metadata.version("httpquoted") == hq.__version__
assert importlib.resources.files("httpquoted").joinpath("py.typed").is_file()

assert hq.quote('a"b\\c') == '"a\\"b\\\\c"'
assert hq.unquote('"a\\"b"', strict=True) == 'a"b'
assert hq.quote_if_needed("utf-8") == "utf-8" and hq.needs_quoting("a b")
assert hq.is_token("max-age") and not hq.is_token("a b")
assert hq.quote_comment("a(b") == "(a\\(b)"
assert hq.unquote_comment("(a (b) \\) c)", strict=True) == "a (b) ) c"
assert hq.scan_quoted_string('x="y", z', 2) == ("y", 5)
assert hq.scan_comment("ua (x (y)) z", 3) == ("x (y)", 10)
assert hq.split_list('a, "b,c", (d, e) f', comments=True) == ["a", '"b,c"', "(d, e) f"]
assert hq.split_list('a; b="c;d"', separator=";") == ["a", 'b="c;d"']
assert hq.unquote(hq.quote(bytes(range(0x80, 0x100)))) == bytes(range(0x80, 0x100))
for call in (
    lambda: hq.quote("a\r\nb"),
    lambda: hq.quote("\xe9", ascii_only=True),
    lambda: hq.unquote('"a"b"', strict=True),
    lambda: hq.split_list('a, "b', strict=True),
    lambda: hq.unquote_comment("(a", strict=True),
):
    try:
        call()
    except hq.QuotedStringError as error:
        assert isinstance(error, ValueError) and error.offset >= 0
    else:
        raise AssertionError("expected QuotedStringError")
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("httpquoted-*.whl")
    (sdist,) = dist.glob("httpquoted-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "httpquoted/py.typed" in names and "httpquoted/__main__.py" in names
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    assert "httpquoted = httpquoted._cli:main" in zipfile.ZipFile(wheel).read(entry_points).decode()
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout.decode()
    assert "IMPROVEMENTS-round" not in listing and "rfc9110.txt" not in listing
    assert "tests/upstream/MANIFEST.json" in listing and "scripts/fetch_upstream.py" in listing
    assert "tests/test_sources.py" in listing

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    script = bindir / ("httpquoted.exe" if sys.platform == "win32" else "httpquoted")
    for command in ([python, "-m", "httpquoted"], [script]):
        shown = _run(*command, "split", "--comments", cwd=work, stdin=b"a, (b, c) d\n")
        assert shown.returncode == 0, shown.stderr
        assert shown.stdout.decode().splitlines() == ["a", "(b, c) d"]
        failed = _run(*command, "unquote", "--strict", '"a"b"', cwd=work)
        assert failed.returncode == 1 and b"text after the closing quote" in failed.stderr
