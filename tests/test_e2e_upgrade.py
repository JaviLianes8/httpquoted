"""Install httpquoted 0.2.0 from PyPI, probe it, upgrade in place to this wheel, probe again.

Needs the network and the build backend, so it runs only with HTTPQUOTED_E2E_PYPI=1. Every
result on valid and invalid input must be identical; only the changes listed in the 1.0.0
section of CHANGELOG.md may differ, and they are checked to differ exactly that way.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("HTTPQUOTED_E2E_PYPI") != "1", reason="set HTTPQUOTED_E2E_PYPI=1 to run"
)

PROBE = r"""
import json, pickle, random, subprocess, sys
import httpquoted as hq

def outcome(call):
    try:
        result = call()
    except hq.QuotedStringError as error:
        return ["QuotedStringError", error.reason, error.offset]
    except (TypeError, ValueError) as error:
        return [type(error).__name__]
    return ["ok", repr(result)]

rng = random.Random(1)
alphabet = list('ab0- \t,;="\\()/') + ["\xe9", "\xff", "\x7f", "\x00", "\n", "\u20ac"]
values = ["".join(rng.choice(alphabet) for _ in range(rng.randrange(10))) for _ in range(600)]
results = []
for value in values:
    for data in (value, value.encode("latin-1", "replace")):
        for strict in (False, True):
            results.append(outcome(lambda: hq.unquote(data, strict=strict)))
            results.append(outcome(lambda: hq.unquote_comment(data, strict=strict)))
            results.append(outcome(lambda: hq.split_list(data, strict=strict)))
            results.append(outcome(lambda: hq.split_list(data, comments=True, strict=strict)))
            results.append(outcome(lambda: hq.split_list(data, separator=";", strict=strict)))
            if data[:1] in ('"', b'"'):
                results.append(outcome(lambda: hq.scan_quoted_string(data, strict=strict)))
            if data[:1] in ("(", b"("):
                results.append(outcome(lambda: hq.scan_comment(data, strict=strict)))
        for ascii_only in (False, True):
            results.append(outcome(lambda: hq.quote(data, ascii_only=ascii_only)))
            results.append(outcome(lambda: hq.quote_comment(data, ascii_only=ascii_only)))
            results.append(outcome(lambda: hq.quote_if_needed(data, ascii_only=ascii_only)))
        results.append(outcome(lambda: hq.is_token(data)))
        results.append(outcome(lambda: hq.needs_quoting(data)))
cli = []
for args, stdin in ((["quote", "a b"], b""), (["unquote", "--strict"], b'"a"b"\n'),
                    (["split", "--comments"], b"a, (b, c) d\n\xff, x\n"), (["nope"], b"")):
    run = subprocess.run([sys.executable, "-m", "httpquoted", *args], input=stdin,
                         capture_output=True)
    cli.append([run.returncode, run.stdout.decode("latin-1")])
changed = {
    "strict_string": outcome(lambda: hq.unquote('"a"', strict="no")),
    "pickle": outcome(lambda: pickle.loads(pickle.dumps(hq.QuotedStringError("r", 1))).offset),
    "module": hq.quote.__module__,
}
print(json.dumps({"version": hq.__version__, "results": results, "cli": cli, "changed": changed}))
"""


def _run(*cmd: str | Path, cwd: Path | None = None) -> str:
    done = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_upgrade_from_pypi_0_2_0_keeps_every_result(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _run(sys.executable, "-m", "build", "--wheel", "--outdir", dist, ROOT)
    (wheel,) = dist.glob("httpquoted-1.0.0-*.whl")
    venv.create(tmp_path / "venv", with_pip=True)
    bindir = tmp_path / "venv" / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    work = tmp_path / "work"
    work.mkdir()
    _run(python, "-m", "pip", "install", "-q", "--no-cache-dir", "httpquoted==0.2.0")
    old = json.loads(_run(python, "-I", "-c", PROBE, cwd=work))
    _run(python, "-m", "pip", "install", "-q", "--no-cache-dir", "--upgrade", wheel)
    new = json.loads(_run(python, "-I", "-c", PROBE, cwd=work))

    assert (old["version"], new["version"]) == ("0.2.0", "1.0.0")
    assert len(new["results"]) > 10_000
    assert new["results"] == old["results"]
    assert new["cli"] == old["cli"]
    assert old["changed"] == {
        "strict_string": ["ok", "'a'"],
        "pickle": ["TypeError"],
        "module": "httpquoted._quote",
    }
    assert new["changed"] == {
        "strict_string": ["TypeError"],
        "pickle": ["ok", "1"],
        "module": "httpquoted",
    }
