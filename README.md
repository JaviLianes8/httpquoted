# httpquoted

Strict, typed and zero-dependency codec for the HTTP quoted-string, comment and token
primitives of RFC 9110 section 5.6: safe quoting, strict or lenient parsing, scanners for
hand-written parsers and list splitting that respects quotes and comments.

## Install

```
pip install httpquoted
```

## Usage

Quote a value for a header and read it back. Only DQUOTE and backslash are escaped, as
section 5.6.4 asks of senders, and a value that is a token can travel bare:

```python
from httpquoted import quote, quote_if_needed, unquote

print(quote('say "hi"'))
print(unquote('"say \\"hi\\""'))
print(quote_if_needed("utf-8"), quote_if_needed("two words"))
# "say \"hi\""
# say "hi"
# utf-8 "two words"
```

Quoting refuses what a quoted-string cannot carry, so a CR LF never reaches a header.
Parsing is lenient by default; `strict=True` raises with the broken rule and its offset:

```python
from httpquoted import QuotedStringError, quote, unquote

for call in (lambda: quote("a\r\nX-Injected: 1"), lambda: unquote('"a"b"', strict=True)):
    try:
        call()
    except QuotedStringError as error:
        print(error.reason, error.offset)
print(unquote('"a"b"'))
# U+000D is not allowed 1
# text after the closing quote 3
# a"b
```

Split a list on commas outside quoted-strings, or parameters on semicolons. Fields
whose grammar has comments (Via, User-Agent, Server) pass `comments=True`:

```python
from httpquoted import split_list, unquote

print(split_list('gzip, "a,b", , br'))
print(split_list('text/plain; charset="utf-8"', separator=";"))
print(split_list("1.0 fred (proxy, eu), 1.1 example.net", comments=True))
print([unquote(tag, strict=True) for tag in split_list('"xyzzy", "r2d2xxxx"')])
# ['gzip', '"a,b"', 'br']
# ['text/plain', 'charset="utf-8"']
# ['1.0 fred (proxy, eu)', '1.1 example.net']
# ['xyzzy', 'r2d2xxxx']
```

Comments nest and have their own escaping. The scanners read one quoted-string or
comment inside a larger value and return where it ends:

```python
from httpquoted import quote_comment, scan_comment, scan_quoted_string, unquote_comment

print(quote_comment("Windows NT 10.0; (x64)"))
print(unquote_comment("(a (nested) \\) comment)", strict=True))
text = 'title="a, \\"b\\""; lang=en'
value, end = scan_quoted_string(text, 6, strict=True)
print(value, text[end:])
print(scan_comment("Mozilla/5.0 (X11; Linux) Gecko", 12))
# (Windows NT 10.0; \(x64\))
# a (nested) ) comment
# a, "b" ; lang=en
# ('X11; Linux', 24)
```

Every function takes `str` or `bytes` and returns the same type. Bytes are read as
ISO-8859-1, so the obs-text octets 0x80 to 0xFF round-trip unchanged:

```python
from httpquoted import quote, split_list, unquote

print(quote(b"caf\xe9"))
print(unquote(b'"caf\xe9"', strict=True))
print(split_list(b'a, "b,c"'))
# b'"caf\xe9"'
# b'caf\xe9'
# [b'a', b'"b,c"']
```

## Command line

```
$ httpquoted quote 'say "hi"'
"say \"hi\""
$ httpquoted unquote --strict '"a"b"'
httpquoted: text after the closing quote at offset 3
$ httpquoted split --comments '1.0 fred (proxy, eu), 1.1 example.net'
1.0 fred (proxy, eu)
1.1 example.net
```

Values come from the arguments, or one per line from standard input. `quote` takes
`--comment` and `--ascii-only`; `unquote` takes `--comment` and `--strict`; `split`
takes `--separator`, `--comments` and `--strict`. A rejected value exits with status 1.

## API

| Name | What it does |
|---|---|
| `quote(value, *, ascii_only=False)` | Quoted-string with DQUOTE and backslash escaped; refuses controls, DEL and anything above U+00FF, and obs-text when `ascii_only` |
| `unquote(value, *, strict=False)` | Strips quotes and resolves quoted-pairs; a bare value comes back unchanged. Strict: exactly a token or a quoted-string |
| `quote_if_needed(value, *, ascii_only=False)` | A token unchanged, anything else quoted (parameter values, section 5.6.6) |
| `needs_quoting(value)` | True unless the value is a token |
| `is_token(value)` | True for a non-empty run of tchar |
| `quote_comment(value, *, ascii_only=False)` | Comment with "(", ")" and backslash escaped |
| `unquote_comment(value, *, strict=False)` | Strips the outer parentheses and resolves quoted-pairs; nested comments stay as text |
| `scan_quoted_string(text, start=0, *, strict=False)` | Value of the quoted-string at `start` and the offset after it |
| `scan_comment(text, start=0, *, strict=False)` | Value of the (nested) comment at `start` and the offset after it |
| `split_list(header, *, separator=",", comments=False, strict=False)` | Elements outside quotes (and comments), trimmed, empty ones dropped |
| `QuotedStringError` | `ValueError` with `reason` and `offset` |

Lenient mode never raises on malformed input (unterminated strings run to the end).
Strict mode follows the grammar of RFC 9110 sections 5.6.2 to 5.6.5 to the character;
the tests evaluate that grammar from the fetched RFC and compare it with the functions
for every code point up to U+010F. Every scan is linear in the length of the input,
including a megabyte of backslashes or nested parentheses.

## Why

The quoted-string codec of RFC 9110 sits under almost every HTTP header parser, yet no
small typed library ships it on its own: the stdlib `quopri` handles MIME
quoted-printable (a different thing), and the logic is vendored privately into
frameworks and SDKs, often without the checks that stop header injection. Other
ecosystems expose it directly (Ruby has `Protocol::HTTP::QuotedString`). This is that
primitive, zero-dependency and typed, for the times you parse or build a header by hand.

## Development

`scripts/check.ps1` runs format, lint, `mypy --strict` and the tests. The RFC checks
read the RFCs from `tests/upstream/`, which is not committed: `python
scripts/fetch_upstream.py` downloads them and verifies the sha256 of each against
`tests/upstream/MANIFEST.json`; until then those tests skip. Set `HTTPQUOTED_E2E=1` to
build the wheel and drive it from a fresh virtual environment.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
