# httpquoted

Typed codec for the HTTP quoted-string primitive (RFC 9110): quote, unquote, token check and quote-aware list splitting.

## Install

```
pip install httpquoted
```

## Usage

```python
from httpquoted import quote, unquote, is_token, split_list

quote('a"b')              # '"a\\"b"'
unquote('"a\\"b"')        # 'a"b'

is_token("max-age")       # True
is_token("a b")           # False

split_list('gzip, "a,b", br')   # ['gzip', '"a,b"', 'br']
```

`quote` wraps a value in double quotes and escapes the backslash and the double
quote as quoted-pairs; `unquote` reverses it and leaves a bare token untouched.
`is_token` recognises the `tchar` production (a non-empty run of token
characters). `split_list` splits a comma-separated header value, treating a comma
inside a quoted-string as data rather than a separator.

## Why

The quoted-string codec in RFC 9110 section 5.6.4 sits under almost every HTTP
header parser, yet no small typed library ships it on its own: the stdlib
`quopri` handles MIME quoted-printable (a different thing), and the logic is
vendored privately into frameworks and SDKs. Other ecosystems expose it directly
(Ruby has `Protocol::HTTP::QuotedString`). This is that primitive, zero-dependency
and typed, for the times you parse or build a header by hand.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
