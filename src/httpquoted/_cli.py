"""Command line: quote, unquote or split header values from arguments or standard input."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ._chars import QuotedStringError
from ._comment import quote_comment, unquote_comment
from ._quote import quote, unquote
from ._split import split_list


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="httpquoted",
        description="Quote, unquote or split HTTP field values (RFC 9110 section 5.6). "
        "Values come from the arguments, or one per line from standard input.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("quote", "write each value as a quoted-string"),
        ("unquote", "read each quoted-string or token back"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("--comment", action="store_true", help="use (comment) syntax")
        if name == "quote":
            command.add_argument("--ascii-only", action="store_true", help="refuse obs-text")
        else:
            command.add_argument("--strict", action="store_true", help="reject malformed input")
        command.add_argument("values", nargs="*")
    split = commands.add_parser("split", help="print each list element on its own line")
    split.add_argument("--separator", default=",", help='"," (default) or ";" for parameters')
    split.add_argument("--comments", action="store_true", help="skip (comments) as a unit")
    split.add_argument("--strict", action="store_true", help="reject malformed input")
    split.add_argument("values", nargs="*")
    return parser


def _convert(args: argparse.Namespace, value: str) -> list[str]:
    if args.command == "quote":
        encode = quote_comment if args.comment else quote
        return [encode(value, ascii_only=args.ascii_only)]
    if args.command == "unquote":
        decode = unquote_comment if args.comment else unquote
        return [decode(value, strict=args.strict)]
    return split_list(value, separator=args.separator, comments=args.comments, strict=args.strict)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the `httpquoted` command; returns the exit status."""
    parser = _parser()
    args = parser.parse_args(argv)
    values = args.values or [line.rstrip("\r\n") for line in sys.stdin]
    try:
        for value in values:
            for line in _convert(args, value):
                print(line)
    except QuotedStringError as error:
        print(f"httpquoted: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        parser.error(str(error))
    return 0
