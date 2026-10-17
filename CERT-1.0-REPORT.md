# httpquoted 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.0, 7cbdbba; PyPI has 0.2.0)
- [x] Baseline gates run on 0.2.0
- [x] API review and 1.0.0 API changes (item 1)
- [x] Real ground truth: fetched sources and live reference parsers (item 7)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.0 (items 8, 10, 13, 14), author run
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] Gates (item 15), final run
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.2.0 (before any change)

Fresh clone of `main` (7cbdbba) on Elena's PC, CPython 3.14.2, references fetched:
`ruff format --check .`, `ruff check .` and `mypy --strict src tests scripts` exit 0;
`pytest` with `HTTPQUOTED_E2E=1` 355 passed. PyPI has 0.2.0 only (0.1.0 was never
published there).

Defects of 0.2.0 found by the API review, each checked against the real 0.2.0 from PyPI
(the upgrade test probes them):

- `QuotedStringError` could be pickled but not unpickled (`TypeError`: the constructor
  needs `offset`).
- `strict`, `ascii_only` and `comments` used the truth value of anything: `strict="no"`
  and `comments=0` were accepted.
- A `TypeError` message echoed the whole type name (100,027 characters for a class with
  a 100,000-character name).
- Public names reported private modules (`httpquoted._quote`) in reprs and pickles.
- Command line: on POSIX an argument was read as file system text, so a UTF-8 argument
  came out as ISO-8859-1 octets while the same value on standard input passed through
  unchanged; Ctrl+C and a closed output (`| head`) gave a traceback.
- Packaging: the sdist took every file not ignored by git, so a local virtual
  environment named `.v` (and a scratch job file) was packed; seen in the first author
  build and fixed with an explicit file list.
- The README linked LICENSE relatively (broken on PyPI) and there was no GUIDE.

## API review (item 1)

Kept from 0.2.0 with the same names, signatures, defaults and results: all eleven
public names. `tests/test_contract_api.py` freezes every signature, the module name of
every public name, pickling, the option type checks and bounded messages. Changed, all
in CHANGELOG 1.0.0 with an upgrade list: options must be `bool`; the error pickles;
public names report `httpquoted`; type names in messages are cut to 40 characters;
command line argument octets on POSIX, exit 130 on interrupt, exit 1 on a closed output,
`VALUE` and `SEP` in the help. Considered and kept: lenient `unquote` and
`unquote_comment` keep the 0.1 rule (strip the first and last character when they are
the delimiters), which is also what Werkzeug's `unquote_header_value` does; `split_list`
raises plain `ValueError` for a bad separator (an argument error, not a grammar error);
the scanners raise `QuotedStringError` for a `start` that is not on the opener, as in
0.2.0.

## Ground truth (item 7)

`scripts/fetch_upstream.py` downloads nine sources into the git-ignored `tests/upstream/`
and checks them against `tests/upstream/MANIFEST.json` (URL, revision, date, size,
SHA-256, licence; fetched 2026-10-13 and 2026-10-17): RFC 9110, 9111, 7230, 7616, 6266
and 5234, the WHATWG Fetch Standard source at a pinned commit, CPython's
`Lib/test/test_urllib2.py` at a pinned commit and Werkzeug 3.1.9's `tests/test_http.py`.
Third-party files are saved with a `.txt` suffix so no tool collects or lints them, and
they are never committed or shipped.

- `tests/test_sources.py` (from 0.2.0): qdtext, ctext, tchar, obs-text and quoted-pair
  are evaluated from the ABNF in the fetched RFC 9110 and RFC 5234 and compared with the
  library for every code point up to U+010F; RFC 7230 has the same sets; the list,
  media type and entity tag examples of RFC 9110.
- `tests/test_examples.py`: the `WWW-Authenticate` example of RFC 9110 section 11.6.1
  (an escaped DQUOTE inside `title`), the `community="UCI"` directive of RFC 9111, the
  three Digest challenges of RFC 7616 (a comma inside `qop="auth, auth-int"`), the four
  `Content-Disposition` examples of RFC 6266, CPython's four `parse_http_list` vectors
  and Werkzeug's seven `parse_list_header` vectors, each read from the fetched file.
- `tests/test_whatwg.py`: a labelled hand transcription of "collect an HTTP quoted
  string" and "get, decode, and split" (`tests/whatwg_reference.py`); the step sentences
  are checked in the fetched standard, the transcription and the library both pass the
  standard's example tables (3 quoted strings, 11 header lists), and 24,000 seeded inputs
  (str and bytes) give the same results: lenient `scan_quoted_string` is the algorithm,
  `split_list` is the split without empty values.
- `tests/test_oracle.py` with `tests/fixtures/oracle_runs.json` (program output recorded
  by `scripts/oracle_fixture.py`, CPython 3.13.2, Werkzeug 3.1.9, h11 0.16.0, Node
  v24.18.0; 2,351 seeded cases): Werkzeug `quote_header_value` equals `quote_if_needed`,
  `unquote_header_value` equals lenient `unquote`, `parse_list_header` equals split then
  unquote except that it returns `[]` for an unclosed quoted-string (checked to raise
  "unterminated" in strict mode); `urllib.request.parse_http_list` splits at the same
  commas (it keeps empty items and drops pair backslashes); `email.utils.quote` escapes
  the same characters and `email.utils.unquote` reads `quote` output back; h11 accepts
  the same tokens and, in field values, exactly the controls 0x01 to 0x08, 0x0E to 0x1F
  and 0x7F more than RFC 9110 allows; Node's `util.MIMEType` reads every quoted
  parameter value as `scan_quoted_string` does. The Werkzeug, h11 and Node answers are
  rerun live when those versions are installed (pinned in the dev extras); the standard
  library is always run live.

## Errors, typing, docs (items 2 to 5)

- `__all__` lists the eleven public names; `tests/test_contract.py` and
  `tests/test_contract_api.py` pin it, the signatures and the module names.
- Every public name has a runnable docstring example (29 examples), run from the public
  names by `test_every_public_name_has_a_passing_example`; every README example and
  command runs in `tests/test_docs.py`, and the GUIDE usage lines match the parser.
- `mypy --strict src tests scripts` clean; `py.typed` shipped; no `Any` in the public API.
- Errors: GUIDE table of every reason and offset; messages never quote the input (ten
  hostile 140,000-character cases stay under 80 characters with no input text); type
  names cut to 40 characters, a non-string `__name__` reported as `object`.

## Contracts, fuzz and mutations (items 6, 9, 18)

New contract files: `test_contract_api.py`, `test_contract_cli.py` (real processes for
each exit status, octets on POSIX and Windows paths), `test_whatwg.py`, `test_oracle.py`,
`test_examples.py`, `test_e2e_upgrade.py`. Fuzz: the seeded property tests of 0.2.0, the
24,000 WHATWG comparisons and the 2,351 oracle cases; `test_hostile.py` runs thirteen
functions on eleven one-megabyte hostile patterns within a linear time budget.

Author mutation round: 67 mutations over every module, each applied alone to a fresh
clone of the pushed branch at 7a46ccb on this PC (CPython 3.13.2, under a turn), suite
with `-x`, no bytecode and a 300-second timeout, the two end-to-end modules left out for
time, file restored after; baseline green before.

| Id | Module | Mutation | Caught by |
| --- | --- | --- | --- |
| C01 | `_chars` | token loses the vertical bar | `test_oracle::test_h11_token_is_is_token` |
| C02 | `_chars` | qdtext includes DQUOTE | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| C03 | `_chars` | qdtext drops obs-text | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| C04 | `_chars` | ctext includes ( | `test_bytes::test_scanners_return_bytes_and_octet_offsets` |
| C05 | `_chars` | field text accepts DEL | `test_oracle::test_h11_field_content_differs_only_on_controls_rfc_9110_refuses` |
| C06 | `_chars` | ascii_only accepts obs-text | `test_bytes::test_quote_refuses_control_octets_and_obs_text_when_ascii_only` |
| C07 | `_chars` | reason kinds swapped | `test_cli::test_quote_comment_and_ascii_only` |
| C08 | `_chars` | field text offset off by one | `test_cli::test_quote_comment_and_ascii_only` |
| C09 | `_chars` | bytes read as UTF-8 | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| C10 | `_chars` | bytes written as UTF-8 | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| C11 | `_chars` | type name bound 400 | `test_contract_api::test_a_type_name_in_a_message_is_bounded` |
| C12 | `_chars` | int accepted as flag | `test_contract_api::test_options_must_be_real_bools[0-quote-ascii_only]` |
| C13 | `_chars` | pickling loses the offset | `test_contract_api::test_the_error_survives_pickling` |
| C14 | `_chars` | HTAB not field text | `test_oracle::test_werkzeug_parse_list_header_is_split_then_unquote` |
| C15 | `_chars` | code point in lower case | `test_cli::test_quote_comment_and_ascii_only` |
| Q01 | `_quote` | quote leaves backslash unescaped | `test_contract_api::test_every_public_name_has_a_passing_example` |
| Q02 | `_quote` | quote escapes in the wrong order | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| Q03 | `_quote` | quote_if_needed takes a token prefix | `test_bytes::test_token_checks_accept_bytes` |
| Q04 | `_quote` | lone quote stripped | `test_oracle::test_werkzeug_unquote_header_value_is_lenient_unquote` |
| Q05 | `_quote` | text after the quote accepted | `test_cli::test_unquote_strict_exits_one_with_the_reason` |
| Q06 | `_quote` | strict unquote takes a token prefix | `test_contract_api::test_error_messages_never_echo_the_input[<lambda>3]` |
| Q07 | `_quote` | non-token offset always 0 | `test_quote::test_strict_unquote_rejects_malformed_values[a b-not a token or a quoted-string-1]` |
| Q08 | `_quote` | lenient pair skips LF | `test_quote::test_lenient_unquote_resolves_a_quoted_pair_of_any_character` |
| Q09 | `_quote` | lenient resolves only escaped quotes | `test_bytes::test_comment_codec_keeps_bytes` |
| Q10 | `_quote` | quote_if_needed skips the flag check | `test_contract_api::test_options_must_be_real_bools[None-quote_if_needed-ascii_only]` |
| K01 | `_comment` | comment leaves backslash unescaped | `test_comment::test_quote_comment_escapes_parentheses_and_backslash_only` |
| K02 | `_comment` | comment leaves ) unescaped | `test_comment::test_quote_comment_escapes_parentheses_and_backslash_only` |
| K03 | `_comment` | text after the comment accepted | `test_comment::test_strict_unquote_comment_rejects_malformed_values[(a) b-text after the closing parenthesis-3]` |
| K04 | `_comment` | lenient comment strips without ) | `test_comment::test_unquote_comment_returns_a_value_without_parentheses_unchanged` |
| S01 | `_scan` | start at the end accepted | `test_comment::test_strict_unquote_comment_rejects_malformed_values[-a comment must start with (-0]` |
| S02 | `_scan` | bool start accepted | `test_review_fixes::test_scanners_refuse_a_start_that_is_not_an_int[True]` |
| S03 | `_scan` | unterminated offset at the end | `test_comment::test_strict_unquote_comment_rejects_malformed_values[(a-unterminated comment-0]` |
| S04 | `_scan` | trailing backslash dropped | `test_oracle::test_node_mime_type_parameters_read_the_scanned_value` |
| S05 | `_scan` | strict pair refuses only NUL CR LF | `test_scan::test_strict_scan_comment_reports_the_broken_rule[(a\\\x7f)-U+007F cannot be quoted-3]` |
| S06 | `_scan` | end offset on the closer | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| S07 | `_scan` | nested comment closes early | `test_bytes::test_scanners_return_bytes_and_octet_offsets` |
| S08 | `_scan` | first nesting not counted | `test_bytes::test_scanners_return_bytes_and_octet_offsets` |
| S09 | `_scan` | pair offset on the backslash | `test_quote::test_strict_unquote_rejects_malformed_values["a\\\nb"-U+000A cannot be quoted-3]` |
| S10 | `_scan` | bad char offset off by one | `test_comment::test_strict_unquote_comment_rejects_malformed_values[(a\x00)-U+0000 is not allowed in a comment-2]` |
| S11 | `_scan` | escaped char read twice | `test_bytes::test_quote_and_unquote_keep_bytes_as_bytes` |
| S12 | `_scan` | scan_comment skips the flag check | `test_contract_api::test_options_must_be_real_bools[None-scan_comment-strict]` |
| P01 | `_split` | tabs not trimmed | `test_oracle::test_werkzeug_parse_list_header_is_split_then_unquote` |
| P02 | `_split` | empty elements kept | `test_contract_api::test_every_public_name_has_a_passing_example` |
| P03 | `_split` | strict split skips field text | `test_contract_api::test_error_messages_never_echo_the_input[<lambda>8]` |
| P04 | `_split` | comments flag inverted | `test_bytes::test_split_list_returns_bytes_elements` |
| P05 | `_split` | stray ) accepted | `test_contract_api::test_error_messages_never_echo_the_input[<lambda>9]` |
| P06 | `_split` | reserved separator accepted | `test_contract_cli::test_exit_statuses_in_a_real_process[args7-2]` |
| P07 | `_split` | control separator accepted | `test_review_fixes::test_split_list_refuses_a_separator_that_is_not_one_field_character[\u20ac]` |
| P08 | `_split` | long separator accepted | survived; equivalent (see below) |
| P09 | `_split` | separator not escaped | `test_split::test_split_list_takes_regex_metacharacters_literally[^]` |
| P10 | `_split` | last element dropped | `test_bytes::test_split_list_returns_bytes_elements` |
| P11 | `_split` | strict not passed to quoted scan | `test_cli::test_split_options` |
| P12 | `_split` | strict not passed to comment scan | `test_contract_cli::test_exit_statuses_in_a_real_process[args3-1]` |
| T01 | `_token` | empty value needs no quoting | `test_bytes::test_token_checks_accept_bytes` |
| L01 | `_cli` | rejected value exits 2 | `test_cli::test_quote_comment_and_ascii_only` |
| L02 | `_cli` | interrupt exits 1 | `test_contract_cli::test_an_interrupt_exits_130_without_a_traceback` |
| L03 | `_cli` | closed output exits 0 | `test_contract_cli::test_a_closed_output_exits_1_quietly` |
| L04 | `_cli` | argument octets on the wrong platform | `test_contract_cli::test_posix_arguments_are_read_back_as_their_octets` |
| L05 | `_cli` | octets applied to main(argv) | `test_contract_cli::test_arguments_passed_to_main_are_used_as_given` |
| L06 | `_cli` | CR kept on input lines | `test_cli::test_unquote_reads_values_from_standard_input` |
| L07 | `_cli` | trailing empty line kept | `test_cli::test_unquote_reads_values_from_standard_input` |
| L08 | `_cli` | stdin read as UTF-8 | `test_contract_cli::test_standard_input_is_read_and_written_as_octets_in_a_real_process` |
| L09 | `_cli` | --strict ignored | `test_cli::test_unquote_strict_exits_one_with_the_reason` |
| L10 | `_cli` | --comments ignored | `test_cli::test_split_options` |
| L11 | `_cli` | --ascii-only ignored | `test_cli::test_quote_comment_and_ascii_only` |
| L12 | `_cli` | stdout written as UTF-8 | `test_contract_cli::test_standard_input_is_read_and_written_as_octets_in_a_real_process` |
| I01 | `__init__` | public names keep private modules | `test_contract_api::test_public_names_report_the_package_as_their_module` |

Result: 66 killed. P08 survived and is equivalent: a separator longer than one
character is never a member of the one-character set `FIELD_TEXT`, so the next check
refuses it with the same error; the length test is kept for readability.

## Independent QA lenses (item 19)

Each lens was a fresh reviewer that read the certification rules and CERT-1.0.md first,
ran the code rather than only reading it, reported only to the author and posted nothing
to GitHub. Lenses ran one at a time. Later rounds were bounded to confirming earlier
findings plus one sweep of at most 40 mutations on the code changed since.

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | e6f1ea9 | FAIL | 390,918 seeded calls against the real 0.2.0: every difference listed in the CHANGELOG; every docstring, README and GUIDE claim run (Werkzeug, h11, urllib, email, WHATWG, Node rechecked with its own scripts); strict consumer clean. Finding: on Windows a closed output raised `OSError(EINVAL)`, not `BrokenPipeError`, so `split \| head -1` exited 120 with a traceback. Low: `inspect.getsource` of the error class fails after the module rename (documented), a `str \| bytes` value is refused by `AnyStr` under mypy (documented), `annotations` leaked from `__init__`; nits on GUIDE rows and CHANGELOG dates. Fixed in e3a9166 with a real-subprocess contract |
| a | 2 | e3a9166 | PASS | all confirmed; Windows repro exits 1 with empty stderr (local 3.13, installed entry point on 3.14); 17 mutants on the changed code, 15 killed, 1 equivalent, 1 (the `__future__` import back) closed by `test_the_module_exposes_nothing_public_beyond_all`; nit: the handler also covered reading stdin, narrowed to the writes with two more contracts |
| b. Correctness and ground truth | 1 | 13ee3e3 | PASS (3 informational) | all nine sources fetched in its run match the manifest (and the live Fetch page matches the pinned source); own reference built from the fetched ABNF and its own WHATWG transcription: 1,808,598 inputs (every string up to length 5 over a 17-character hostile alphabet plus 300,000 seeded), 66,721,887 comparisons in str and bytes, 538,841 round trips, all 1,114,112 code points per class, 400,000 strict scans at non-zero starts: 0 mismatches; oracle fixture regenerated identically; Werkzeug, h11, urllib, email and Node rerun on its own inputs, each GUIDE statement confirmed. Notes: urllib differs on malformed values ending in a backslash (GUIDE now says "well-formed"), the unterminated comment offset is the outermost parenthesis (GUIDE says so), a test helper assumed every quoted-string closes (fixed) |
| c. Adversarial and robustness | 1 | b846b6e | FAIL | seeded fuzz of all eleven names and every option (2,335,782 calls on 3.13.2, more on 3.14.2t): no undocumented exception; 15 hostile patterns x 17 calls from 10 KB to 10 MB: every 1 to 10 MB ratio between 9.1x and 11.3x, at most 26.7 bytes per input character; 16 threads on 3.13 and free-threaded 3.14.2t identical to serial; 93 CLI cases with only exit 0, 1, 2 and no traceback. Findings: a closed stdin or stdout (`0<&-`, `1>&-`) gave a traceback; other write errors (ENOSPC) escaped and a closed stderr mixed reasons into stdout; a `start` of 10**5000 raised a plain `ValueError` and 10**4000 gave a 4,000-character message; an `int` subclass `start` and `str`/`bytes` subclasses could steer results or raise their own errors through overridden methods; a metaclass `__name__` could inflate or break the type name. Fixed in 5d020bb with `tests/test_contract_hostile.py`, each contract confirmed red on the previous code |
