"""Record what established HTTP parsers answer for seeded inputs.

Runs Werkzeug, h11, the standard library (`urllib.request.parse_http_list`,
`email.utils.quote` and `unquote`) and Node's `util.MIMEType` on the same seeded inputs
and writes their answers to tests/fixtures/oracle_runs.json, which tests/test_oracle.py
compares with httpquoted. That file is program output of those tools, not a copy of them.

    pip install werkzeug h11
    python scripts/oracle_fixture.py
"""

from __future__ import annotations

import email.utils
import importlib
import importlib.metadata
import json
import platform
import random
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "oracle_runs.json"
SEED = 9110
# No LF and no other whitespace than SP and HTAB: Werkzeug's unescaping regex has no
# DOTALL and str.strip() trims more than HTAB and SP, two documented differences.
ALPHABET = [*'ab0- \t,;="\\()/', "\xe9", "\xff", "\x7f", "\x01"]
FIELD = [c for c in ALPHABET if c not in "\x7f\x01"]
NODE = """
const {MIMEType} = require('util');
const out = JSON.parse(require('fs').readFileSync(0, 'utf8')).map((qs) => {
  try { const v = new MIMEType('x/y;p=' + qs).params.get('p'); return v === null ? null : v; }
  catch (e) { return 'ERROR'; }
});
process.stdout.write(JSON.stringify(out));
"""


def inputs(rng: random.Random, alphabet: list[str], count: int, size: int) -> list[str]:
    return ["".join(rng.choice(alphabet) for _ in range(rng.randrange(size))) for _ in range(count)]


def cases() -> dict[str, list[str]]:
    """The seeded inputs; the same seed always gives the same cases."""
    rng = random.Random(SEED)
    quoted = ['"' + body for body in inputs(rng, FIELD, 400, 10)]
    return {
        "quote": inputs(rng, FIELD, 400, 10),
        "unquote": quoted + inputs(rng, ALPHABET, 400, 10),
        "list": inputs(rng, FIELD, 800, 16),
        "mime": [qs for qs in quoted if qs[-1] not in " \t"],
    }


def python_oracles(case: dict[str, list[str]]) -> dict[str, Any]:
    """Run the Python reference parsers; needs werkzeug and h11 installed."""
    # Imported by name: neither is a dependency of httpquoted, nor of its type check.
    abnf = importlib.import_module("h11._abnf")
    wz = importlib.import_module("werkzeug.http")
    token = abnf.token.encode()
    field = abnf.field_value.encode()
    octets = [bytes([b]) for b in range(256)]
    return {
        "werkzeug_quote": [wz.quote_header_value(v) for v in case["quote"]],
        "werkzeug_unquote": [wz.unquote_header_value(v) for v in case["unquote"]],
        "werkzeug_list": [wz.parse_list_header(v) for v in case["list"]],
        "urllib_list": [urllib.request.parse_http_list(v) for v in case["list"]],
        "email_quote": [email.utils.quote(v) for v in case["quote"]],
        "h11_token": [re.fullmatch(token, o) is not None for o in octets],
        "h11_field": [re.fullmatch(field, b"a" + o + b"b") is not None for o in octets],
    }


def node_oracle(case: dict[str, list[str]]) -> list[str | None] | None:
    """Node's WHATWG MIME type parser on `x/y;p=<quoted-string>`, or None without node."""
    node = shutil.which("node")
    if node is None:
        return None
    run = subprocess.run(
        [node, "-e", NODE],
        input=json.dumps(case["mime"]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    result: list[str | None] = json.loads(run.stdout)
    return result


def node_version() -> str | None:
    node = shutil.which("node")
    if node is None:
        return None
    return subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()


def main() -> int:
    case = cases()
    record: dict[str, Any] = {
        "tools": {
            "python": platform.python_version(),
            "werkzeug": importlib.metadata.version("werkzeug"),
            "h11": importlib.metadata.version("h11"),
            "node": node_version(),
        },
        "seed": SEED,
        "cases": case,
        **python_oracles(case),
        "node_mime": node_oracle(case),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, ensure_ascii=True, indent=0) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {sum(len(v) for v in case.values())} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
