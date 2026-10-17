# httpquoted guide

This guide describes every behaviour of httpquoted 1.0 in detail. The
[README](https://github.com/JaviLianes8/httpquoted/blob/main/README.md) has the quick start.

## The grammar

RFC 9110 section 5.6 defines the pieces this library reads and writes:

| Rule | Characters |
|---|---|
| `tchar` (token) | letters, digits and ``!#$%&'*+-.^_`|~`` |
| `qdtext` | HTAB, SP, `!`, `#` to `[`, `]` to `~`, obs-text |
| `ctext` | HTAB, SP, `!` to `'`, `*` to `[`, `]` to `~`, obs-text |
| `quoted-pair` | backslash followed by HTAB, SP, a visible ASCII character or obs-text |
| `obs-text` | the octets 0x80 to 0xFF |

A quoted-string is `DQUOTE *( qdtext / quoted-pair ) DQUOTE`. A comment is
`"(" *( ctext / quoted-pair / comment ) ")"`, so comments nest, and inside a comment
DQUOTE is plain text. The test suite evaluates these rules from the fetched RFC and
compares them with the library for every code point up to U+010F.

## Writing values

`quote` escapes only DQUOTE and backslash, `quote_comment` only `(`, `)` and backslash,
as section 5.6.4 asks of senders. Both refuse anything a quoted-pair cannot carry: NUL,
CR, LF and the other controls, DEL, and every character above U+00FF. That is what stops
a value from smuggling a line break into a header. With `ascii_only=True` they also
refuse obs-text, which section 5.5 discourages in new fields.

`quote_if_needed` returns a token unchanged and quotes anything else, including the
empty value; `needs_quoting` and `is_token` answer the same question as booleans.

## Reading values: lenient and strict

Every reader has two modes.

- Lenient (the default) never raises on malformed input. `unquote` and
  `unquote_comment` strip the first and last character when they are the quotes (or the
  parentheses) and resolve every backslash pair in between; anything else comes back
  unchanged. The scanners stop at the first unescaped closing quote or matching
  parenthesis and let an unterminated value run to the end of the text; a backslash at
  the very end is kept. This is the "collect an HTTP quoted string" algorithm of the
  WHATWG Fetch Standard, which the tests compare character by character.
- Strict (`strict=True`) checks every character against the grammar and raises
  `QuotedStringError` at the first one that breaks it. `unquote` accepts exactly a token
  or one quoted-string; `unquote_comment` exactly one comment.

`scan_quoted_string(text, start)` and `scan_comment(text, start)` return the value and
the offset just past the closing character, so a hand-written parser can continue from
there. The value of a comment keeps the parentheses of nested comments and has every
quoted-pair resolved, so `\)` and a nesting `)` look alike in it; slice the raw comment
with the returned offset to parse it again.

## Splitting lists

`split_list` splits on a separator outside quoted-strings (and outside comments with
`comments=True`, for Via, User-Agent and Server), trims spaces and tabs around each
element and drops empty elements, as section 5.6.1.2 asks of recipients. Elements keep
their quotes; pass them to `unquote` to read a value. `separator=";"` splits parameters.
The separator must be one field character other than DQUOTE, backslash, `(` and `)`.

Strict mode refuses a character that is not field content and any quoted-string or
comment that breaks its grammar or never ends, and, with `comments=True`, a stray `)`.
It does not check the grammar of each element, which belongs to the field: `"a"b` is
one element.

## str and bytes

Every function takes `str` or `bytes` and returns the same type. Bytes are read as
ISO-8859-1, where each octet is the code point of the same value, so obs-text
round-trips unchanged and every offset is an octet offset. `bytearray`, `memoryview` and
other types raise `TypeError`. The signatures use the `AnyStr` type variable, so a type
checker wants a value known to be `str` or known to be `bytes`; narrow a `str | bytes`
value with `isinstance` before the call.

## Errors

| Error | When |
|---|---|
| `QuotedStringError` | a value breaks the grammar; a subclass of `ValueError` |
| `TypeError` | the value or the separator is not `str` or `bytes`; `strict`, `ascii_only` or `comments` is not a `bool`; `start` is not an `int` |
| `ValueError` | `split_list` was given a separator that cannot split a field value |

`QuotedStringError` carries `reason` and `offset`, and its message is
`"<reason> at offset <offset>"`. It never quotes the input: characters are named by
code point (`U+000A`) and type names are cut to 40 characters, so a huge or secret value
never reaches a log through an error. It survives pickling. The reasons are:

| Reason | Offset points at |
|---|---|
| `U+XXXX is not allowed` | a character `quote`, `quote_comment` or strict `split_list` refuses |
| `U+XXXX is obs-text` | an obs-text character refused by `ascii_only=True` |
| `U+XXXX is not allowed in a quoted-string` (or `comment`) | a character outside qdtext or ctext |
| `U+XXXX cannot be quoted` | the character after a backslash |
| `a quoted-pair needs a character` | a backslash at the end of the text |
| `unterminated quoted-string` (or `comment`) | the opening quote or parenthesis |
| `text after the closing quote` (or `parenthesis`) | the first character after it |
| `not a token or a quoted-string` | the first character that is not a token character |
| `a quoted-string must start with "` (or `comment`, `(`) | the `start` given to a scanner, or 0 for strict `unquote_comment` |
| `unbalanced )` | a stray `)` in `split_list(..., comments=True, strict=True)` |

## Command line

```
httpquoted quote [-h] [--comment] [--ascii-only] [VALUE ...]
httpquoted unquote [-h] [--comment] [--strict] [VALUE ...]
httpquoted split [-h] [--separator SEP] [--comments] [--strict] [VALUE ...]
```

Values come from the arguments, or one per line from standard input. Standard input and
output are read and written as ISO-8859-1, so octets pass through unchanged. On POSIX
systems each argument is read back as the octets it was given; on Windows arguments are
text and each character up to U+00FF is written as that octet. `python -m httpquoted`
works the same way.

| Exit status | Meaning |
|---|---|
| 0 | every value was written |
| 1 | a value was rejected (the reason goes to standard error), or the output closed early |
| 2 | usage error |
| 130 | interrupted |

## Compared with other parsers

The tests run these tools on the same seeded inputs and check each statement below.

- Werkzeug 3.1.9: `quote_header_value` gives the same result as `quote_if_needed`, and
  `unquote_header_value` the same as lenient `unquote` (except after a backslash
  followed by LF). `parse_list_header` gives `[unquote(e) for e in split_list(v)]`,
  but returns an empty list when a quoted-string never closes.
- The standard library: `urllib.request.parse_http_list` splits at the same commas but
  keeps empty items and drops the backslash of each quoted-pair; `email.utils.quote`
  escapes the same two characters as `quote`.
- h11 0.16.0 recognises the same tokens; it accepts the controls 0x01 to 0x08, 0x0E to
  0x1F and 0x7F in a field value, which RFC 9110 does not allow and httpquoted refuses.
- The WHATWG Fetch Standard: lenient `scan_quoted_string` is its "collect an HTTP quoted
  string" algorithm, and `split_list` is its "get, decode, and split" without the empty
  values. Node's `util.MIMEType` reads parameter values the same way.

## Performance and threads

Every function is linear in the length of its input, including a megabyte of
backslashes, quotes or nested parentheses; nesting depth uses no recursion. The functions
keep no state and are safe to call from any number of threads.
