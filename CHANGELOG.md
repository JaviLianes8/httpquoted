# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-17

The public API is now stable: the eleven names in `httpquoted.__all__`, their
signatures, defaults, results and error types, and the `httpquoted` command with its
options and exit statuses. Results on valid input are identical to 0.2.0.

### Changed

- The `strict`, `ascii_only` and `comments` options must be real `bool` values; anything
  else raises `TypeError` (0.2.0 used the truth value, so `strict="no"` meant strict).
- `QuotedStringError` survives pickling (0.2.0 raised `TypeError` when unpickled).
- Public names report `httpquoted` as their module instead of a private module.
- A `TypeError` message names at most 40 characters of the offending type name.
- Command line: on POSIX systems each argument is read back as the octets it was given
  (ISO-8859-1, like standard input) instead of as file system text, so a UTF-8 argument
  is written out unchanged; an interrupt exits with status 130 and a closed output
  (`| head`) with status 1, both without a traceback.

### Upgrading from 0.2.0

- Pass `True` or `False` to `strict`, `ascii_only` and `comments`.
- Code that compared `QuotedStringError.__module__` or a function's `__module__` with
  a private module name now sees `httpquoted`.

## [0.2.0]

### Added

- `QuotedStringError`, a `ValueError` with `reason` and `offset`.
- `strict=True` on `unquote` (exactly a token or a quoted-string) and `split_list`
  (field content only, every quoted-string and comment well formed and closed).
- `scan_quoted_string` and `scan_comment`: read one quoted-string or (nested) comment
  inside a larger value and return its value and end offset.
- `quote_comment` and `unquote_comment` for the comment syntax of section 5.6.5.
- `quote_if_needed` and `needs_quoting` for parameter values (section 5.6.6).
- `split_list` options: `separator` (";" for parameters, `str` or `bytes`) and `comments=True` for Via,
  User-Agent and Server, where a comment may hold commas and a lone DQUOTE.
- `bytes` support everywhere: bytes in, bytes out, read as ISO-8859-1.
- `ascii_only=True` on the quoting functions to refuse obs-text.
- The `httpquoted` command (`quote`, `unquote`, `split`) and `python -m httpquoted`;
  standard input and output are read and written as ISO-8859-1.

### Changed

- `quote` raises `QuotedStringError` for CR, LF, NUL, the other controls, DEL and
  characters above U+00FF instead of writing them into the header.
- Every function raises `TypeError` for input that is neither `str` nor `bytes`;
  `is_token(None)` returned `False` before.

## [0.1.0]

- First release: `quote`, `unquote`, `is_token` and `split_list` for the HTTP
  quoted-string primitive (RFC 9110).
