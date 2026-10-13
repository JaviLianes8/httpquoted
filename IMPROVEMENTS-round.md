# httpquoted improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 9110, RFC 7230 and its errata, RFC 5234 core rules
- [x] Safe quoting: refuse CTLs, DEL and characters above U+00FF; optional ASCII-only mode
- [x] Scanner: quoted-string and comment scanners, strict and lenient, linear time
- [x] Strict unquote and comment codec (nesting, quoted-pairs)
- [x] List splitting: separator, comments, strict mode
- [x] Bytes in, bytes out (ISO-8859-1) across the API
- [x] Command line
- [x] Contracts: pinned sources, RFC examples, round trips, hostile input, README, installed wheel
- [x] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Mutation run: removing guarded logic makes the suite fail
- [x] Independent review findings fixed with regression tests
- [x] Pull request opened (#2), guard clean

## Starting point

`0.1.0` gives `quote`, `unquote`, `is_token` and `split_list`. Probed against the sources:

- `quote("a\r\nX-Evil: 1")` returns the CR LF inside the quotes: a header injection. NUL,
  DEL and characters that ISO-8859-1 cannot carry (U+20AC) pass through as well, although
  `qdtext` and `quoted-pair` only admit HTAB, SP, VCHAR and obs-text.
- `unquote` has no way to say a value is malformed: `"a"b"` gives `a"b` (an unescaped
  DQUOTE), `"a\"` gives `a\` (the closing quote is escaped, so the string never ends).
- Comments (section 5.6.5) are not handled at all: no quoting, no unquoting, and
  `split_list` cuts `1.0 fred (a, b), 1.1 x` inside the comment of a Via value.
- An unterminated quoted-string in `split_list("a, \"b")` is returned as an element
  without notice.
- Only `str` is accepted; field values read off the wire are bytes, and the octets of
  obs-text map one to one onto ISO-8859-1.
- Lists separated by something other than a comma (parameters use `;`) need their own
  splitter, and a hand-written parser has no scanner to find where a quoted-string ends.
- Nothing pins the character sets to the RFC, and the README examples are not run.

## Sources (fetched 2026-10-13)

- RFC 9110, https://www.rfc-editor.org/rfc/rfc9110.txt: section 5.6.1 (lists, empty
  elements and the example list), 5.6.2 (token, tchar, delimiters), 5.6.3 (whitespace),
  5.6.4 (quoted-string, qdtext, quoted-pair, the sender rule on quoted-pairs), 5.6.5
  (comment, ctext, nesting), 5.6.6 (parameters, token and quoted forms are equivalent),
  5.5 (obs-text, CR, LF and NUL are invalid), 8.3.1 (equivalent media types), 13.1.1 and
  13.1.2 (If-Match and If-None-Match examples).
- RFC 7230, https://www.rfc-editor.org/rfc/rfc7230.txt: section 3.2.6, the same grammar
  before RFC 9110. Errata from https://www.rfc-editor.org/errata.json: 4891 (held, a
  missing space in the qdtext rule, no change in meaning), 6333 (rejected, quote marks in
  the PDF rendering of tchar), 4189 (held, field-value cannot carry the inner spaces of a
  comment; RFC 9110 rewrote field-content). None of the 14 RFC 9110 errata touches 5.6.
- RFC 5234, https://www.rfc-editor.org/rfc/rfc5234.txt: core rules HTAB, SP, DQUOTE,
  VCHAR, ALPHA, DIGIT.
- None of these files is committed. `tests/upstream/MANIFEST.json` records URL, size,
  sha256 and licence; `scripts/fetch_upstream.py` fetches and checks them into the
  ignored `tests/upstream/` folder, and their tests skip while they are absent.

## Ranked improvements

1. **Safe quoting.** `quote` raises `QuotedStringError` (a `ValueError`) for any character
   outside HTAB, SP, VCHAR and obs-text, which closes CR LF injection; `ascii_only=True`
   also refuses obs-text, per the advice of section 5.5 for new fields. It only escapes
   DQUOTE and backslash, as section 5.6.4 asks of senders.
2. **Scanners.** `scan_quoted_string(text, start)` and `scan_comment(text, start)` return
   the decoded value and the offset after it, for hand-written parsers. Lenient by
   default; `strict=True` raises with the offset and the broken rule. Comments nest to any
   depth with a counter, not recursion. Runs of plain text are matched with regexes that
   cannot backtrack, so time is linear even on hostile input.
3. **Strict unquote and the comment codec.** `unquote(value, strict=True)` accepts exactly
   a token or a quoted-string. `quote_comment` escapes `(`, `)` and backslash;
   `unquote_comment` strips the outer parentheses and resolves quoted-pairs, keeping
   nested comments as text. Lenient `unquote` keeps the 0.1.0 behaviour.
4. **List splitting.** `split_list` gains `separator` (`;` for parameters),
   `comments=True` for fields whose grammar has comments (inside a comment, DQUOTE is
   ctext and does not open a quoted-string) and `strict=True` (unterminated quoted-string
   or comment, an unbalanced `)`, characters that are not field content).
5. **Bytes.** Every function takes `str` or `bytes` and returns the same type; bytes are
   read as ISO-8859-1 so obs-text survives a round trip octet for octet.
6. **Typed API.** `AnyStr` signatures, keyword-only options, one error type with `reason`
   and `offset`, `py.typed`.
7. **Helpers.** `needs_quoting` and `quote_if_needed` for parameter values, which may be a
   token or a quoted-string (section 5.6.6).
8. **Contracts.** Character sets read from the fetched RFC grammar, the RFC examples run
   through the API, seeded round-trip properties (quote then strict unquote, scanner
   offsets, split then join), hostile input of a megabyte in linear time, README examples
   executed, the installed wheel driven from an empty folder.
9. **Command line.** `httpquoted quote|unquote|split` for shell scripts that build or read
   a header; it fits only as a thin layer, so it stays small.
10. **Docs and packaging.** README with executed examples and an API table, CHANGELOG,
    keywords and classifiers, an sdist without planning notes or fetched files.

## Out of scope

- Parsing whole fields (parameters into a dict, media types, ETags): other libraries in
  the catalogue do that on top of this primitive.
- obs-fold and field line handling (RFC 9112): the input is one field value.
- RFC 8187 ext-values (`name*=UTF-8''...`) and Structured Fields (RFC 9651), which have
  their own string syntax.

## Verification

Run on a clean clone of the branch on a build machine (Python 3.14, Windows), with the
reference files fetched and checked against the manifest:

- Gates: ruff format, ruff check, mypy --strict (src, and src with tests) and pytest
  exit 0; the installed-wheel test ran (`HTTPQUOTED_E2E=1`) and no test skipped.
- Mutation run: 60 mutants, each removing or bending one guard (character classes, the
  CR LF and DEL refusal, obs-text and `ascii_only`, quoted-pair checks, nesting depth,
  end offsets, strict trailing text, separator validation and escaping, comment mode,
  element trimming, the bytes bridge, a quadratic split loop, the CLI octet handling and
  exit codes). The first
  pass left two alive (a quoted-pair of a line break in lenient `unquote`, and a `^`
  separator before a quoted-string); both have tests now and die. Baseline green before
  and after.

## Independent review

No high-severity findings. Fixed, each with a test in `tests/test_review_fixes.py`:

- The command line read standard input with the locale codec and wrote with it, so
  obs-text octets were mangled or crashed as a usage error; it now reads and writes
  ISO-8859-1, splits lines only on LF (never on U+0085), and a value that is not an
  octet exits 1 with a clear message instead of a usage error.
- `split_list` took only a `str` separator; it now takes `str` or `bytes` and refuses a
  separator that is not one field character (above U+00FF, a control, DEL).
- With `ascii_only=True` the error pointed at a later control instead of the first
  obs-text character; one character class now finds the first refused character.
- The scanners accepted `True` as an offset; a non-int start raises `TypeError`.
- Docs: what strict `split_list` checks (field content and every quoted-string and
  comment, not the element grammar), the different lenient behaviour of `unquote` and
  the scanners, comment values as display text (slice the raw comment with the end
  offset to parse it again), C1 controls inside obs-text, the `TypeError` change in the
  CHANGELOG.
- Tests: the hostile matrix covers bytes and `quote_if_needed`, a misnamed test was
  renamed, the em-dash walk skips ignored folders; the fetch script reports every file
  that fails and `check.ps1` type-checks `scripts/`.
