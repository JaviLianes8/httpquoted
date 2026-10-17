"""Command line: quote, unquote or split header values from arguments or standard input."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Sequence

from ._chars import QuotedStringError
from ._comment import quote_comment, unquote_comment
from ._quote import quote, unquote
from ._split import check_separator, split_list


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
        command.add_argument("values", nargs="*", metavar="VALUE")
    split = commands.add_parser("split", help="print each list element on its own line")
    split.add_argument(
        "--separator", default=",", metavar="SEP", help='"," (default) or ";" for parameters'
    )
    split.add_argument("--comments", action="store_true", help="skip (comments) as a unit")
    split.add_argument("--strict", action="store_true", help="reject malformed input")
    split.add_argument("values", nargs="*", metavar="VALUE")
    return parser


def _convert(args: argparse.Namespace, value: str) -> list[str]:
    if args.command == "quote":
        encode = quote_comment if args.comment else quote
        return [encode(value, ascii_only=args.ascii_only)]
    if args.command == "unquote":
        decode = unquote_comment if args.comment else unquote
        return [decode(value, strict=args.strict)]
    return split_list(value, separator=args.separator, comments=args.comments, strict=args.strict)


def _read_lines() -> list[str]:
    # Field values are octets: read standard input as ISO-8859-1, never the locale codec.
    buffer = getattr(sys.stdin, "buffer", None)
    data = buffer.read().decode("latin-1") if buffer is not None else sys.stdin.read()
    lines = [line.removesuffix("\r") for line in data.split("\n")]
    return lines[:-1] if lines and not lines[-1] else lines


def _write_line(line: str) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(line + "\n")
        return
    sys.stdout.flush()
    buffer.write(line.encode("latin-1") + b"\n")
    buffer.flush()


def _octets(arg: str) -> str:
    # POSIX hands arguments over as bytes decoded with the file system codec: recover those
    # octets so an argument reads as ISO-8859-1, like standard input. Windows passes text.
    if sys.platform == "win32":
        return arg
    return os.fsencode(arg).decode("latin-1")


def _silence_stdout() -> None:
    # The reader went away: point stdout at the null device so the final flush at exit
    # cannot fail again and print a traceback.
    with contextlib.suppress(OSError, ValueError, AttributeError):
        target = sys.stdout.fileno()
        null = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(null, target)
        finally:
            os.close(null)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the `httpquoted` command; returns the exit status.

    0 when every value was written, 1 when one is rejected or the output closes early,
    2 for a usage error and 130 when interrupted.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    if argv is None:
        args.values = [_octets(value) for value in args.values]
        if args.command == "split":
            args.separator = _octets(args.separator)
    if args.command == "split":
        try:
            check_separator(args.separator)
        except ValueError as error:
            parser.error(str(error))
    try:
        for value in args.values or _read_lines():
            for line in _convert(args, value):
                _write_line(line)
    except QuotedStringError as error:
        print(f"httpquoted: {error}", file=sys.stderr)
        return 1
    except UnicodeEncodeError as error:
        char = error.object[error.start]
        print(f"httpquoted: U+{ord(char):04X} is not an ISO-8859-1 octet", file=sys.stderr)
        return 1
    except BrokenPipeError:
        _silence_stdout()
        return 1
    except KeyboardInterrupt:
        return 130
    return 0
