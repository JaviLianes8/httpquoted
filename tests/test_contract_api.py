"""The frozen 1.0 surface: signatures, module names, option types, errors and examples."""

from __future__ import annotations

import doctest
import inspect
import pickle
from collections.abc import Callable
from typing import Any

import pytest

import httpquoted as hq

SIGNATURES = {
    "is_token": "(value: 'AnyStr') -> 'bool'",
    "needs_quoting": "(value: 'AnyStr') -> 'bool'",
    "quote": "(value: 'AnyStr', *, ascii_only: 'bool' = False) -> 'AnyStr'",
    "quote_comment": "(value: 'AnyStr', *, ascii_only: 'bool' = False) -> 'AnyStr'",
    "quote_if_needed": "(value: 'AnyStr', *, ascii_only: 'bool' = False) -> 'AnyStr'",
    "scan_comment": (
        "(text: 'AnyStr', start: 'int' = 0, *, strict: 'bool' = False) -> 'tuple[AnyStr, int]'"
    ),
    "scan_quoted_string": (
        "(text: 'AnyStr', start: 'int' = 0, *, strict: 'bool' = False) -> 'tuple[AnyStr, int]'"
    ),
    "split_list": (
        "(header: 'AnyStr', *, separator: 'str | bytes' = ',', comments: 'bool' = False, "
        "strict: 'bool' = False) -> 'list[AnyStr]'"
    ),
    "unquote": "(value: 'AnyStr', *, strict: 'bool' = False) -> 'AnyStr'",
    "unquote_comment": "(value: 'AnyStr', *, strict: 'bool' = False) -> 'AnyStr'",
    "QuotedStringError": "(reason: 'str', offset: 'int') -> 'None'",
}

FLAGS: list[tuple[str, str]] = [
    ("quote", "ascii_only"),
    ("quote_if_needed", "ascii_only"),
    ("quote_comment", "ascii_only"),
    ("unquote", "strict"),
    ("unquote_comment", "strict"),
    ("scan_quoted_string", "strict"),
    ("scan_comment", "strict"),
    ("split_list", "strict"),
    ("split_list", "comments"),
]
SAMPLE = {"scan_quoted_string": '"a"', "scan_comment": "(a)", "unquote_comment": "(a)"}


def test_every_public_signature_is_frozen() -> None:
    assert set(SIGNATURES) == set(hq.__all__)
    for name, expected in SIGNATURES.items():
        assert str(inspect.signature(getattr(hq, name))) == expected, name


def test_public_names_report_the_package_as_their_module() -> None:
    for name in hq.__all__:
        assert getattr(hq, name).__module__ == "httpquoted", name
    assert repr(hq.QuotedStringError("bad", 1)) == "QuotedStringError('bad at offset 1')"


def test_the_error_survives_pickling() -> None:
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        error = pickle.loads(pickle.dumps(hq.QuotedStringError("bad", 7), protocol))
        assert type(error) is hq.QuotedStringError
        assert (error.reason, error.offset, str(error)) == ("bad", 7, "bad at offset 7")


@pytest.mark.parametrize(("name", "flag"), FLAGS)
@pytest.mark.parametrize("value", [None, 0, 1, "yes", "", 1.0, [], b"x"])
def test_options_must_be_real_bools(name: str, flag: str, value: object) -> None:
    function: Callable[..., Any] = getattr(hq, name)
    sample = SAMPLE.get(name, "token")
    with pytest.raises(TypeError) as caught:
        function(sample, **{flag: value})
    assert str(caught.value) == f"{flag} must be a bool, got {type(value).__name__}"
    for good in (False, True):
        function(sample, **{flag: good})


def test_a_type_name_in_a_message_is_bounded() -> None:
    long_name = type("N" * 100_000, (), {})()
    for call in (
        lambda: hq.quote(long_name),
        lambda: hq.unquote("a", strict=long_name),
        lambda: hq.scan_comment("(a)", long_name),
        lambda: hq.split_list("a", separator=long_name),
    ):
        with pytest.raises(TypeError) as caught:
            call()
        assert str(caught.value).endswith("got " + "N" * 40)

    class Meta(type):
        __name__ = property(lambda cls: 5)

    odd = Meta("Odd", (), {})()
    with pytest.raises(TypeError, match=r"got Odd$"):
        hq.is_token(odd)


SECRET = "s3cr3t-" * 20_000


@pytest.mark.parametrize(
    "call",
    [
        lambda: hq.quote(SECRET + "\n"),
        lambda: hq.quote_comment(SECRET + "\x00"),
        lambda: hq.quote(SECRET + "\xe9", ascii_only=True),
        lambda: hq.unquote(SECRET + " x", strict=True),
        lambda: hq.unquote('"' + SECRET, strict=True),
        lambda: hq.unquote_comment("(" + SECRET + "))", strict=True),
        lambda: hq.scan_quoted_string(SECRET),
        lambda: hq.scan_comment("(" + SECRET + "\x7f)", strict=True),
        lambda: hq.split_list(SECRET + "\r\n", strict=True),
        lambda: hq.split_list(SECRET + ")", comments=True, strict=True),
    ],
)
def test_error_messages_never_echo_the_input(call: Callable[[], object]) -> None:
    with pytest.raises(hq.QuotedStringError) as caught:
        call()
    message = str(caught.value)
    assert "s3cr3t" not in message and len(message) < 80
    assert message == f"{caught.value.reason} at offset {caught.value.offset}"


def test_quote_if_needed_checks_its_option_before_returning_a_token() -> None:
    with pytest.raises(TypeError):
        hq.quote_if_needed("token", ascii_only=None)  # type: ignore[arg-type]


def test_every_public_name_has_a_passing_example() -> None:
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    finder = doctest.DocTestFinder(recurse=False)
    for name in hq.__all__:
        tests = finder.find(getattr(hq, name), name, globs={})
        assert tests and tests[0].examples, name
        for test in tests:
            runner.run(test)
    assert runner.summarize(verbose=False).failed == 0
