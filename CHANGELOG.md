# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- `QuotedStringError`, a `ValueError` with `reason` and `offset`.
- `strict=True` on `unquote` and `split_list`: the value must follow the grammar of
  RFC 9110 section 5.6, character by character.
- `scan_quoted_string` and `scan_comment`: read one quoted-string or (nested) comment
  inside a larger value and return its value and end offset.
- `quote_comment` and `unquote_comment` for the comment syntax of section 5.6.5.
- `quote_if_needed` and `needs_quoting` for parameter values (section 5.6.6).
- `split_list` options: `separator` (";" for parameters) and `comments=True` for Via,
  User-Agent and Server, where a comment may hold commas and a lone DQUOTE.
- `bytes` support everywhere: bytes in, bytes out, read as ISO-8859-1.
- `ascii_only=True` on the quoting functions to refuse obs-text.
- The `httpquoted` command (`quote`, `unquote`, `split`) and `python -m httpquoted`.

### Changed

- `quote` raises `QuotedStringError` for CR, LF, NUL, the other controls, DEL and
  characters above U+00FF instead of writing them into the header.
- `is_token` uses one regular expression; ASCII only, as before.


## [0.1.0]

- First release: `quote`, `unquote`, `is_token` and `split_list` for the HTTP
  quoted-string primitive (RFC 9110).
