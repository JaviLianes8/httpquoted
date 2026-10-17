import importlib.resources
import inspect

import httpquoted

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "QuotedStringError",
    "is_token",
    "needs_quoting",
    "quote",
    "quote_comment",
    "quote_if_needed",
    "scan_comment",
    "scan_quoted_string",
    "split_list",
    "unquote",
    "unquote_comment",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(httpquoted.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in httpquoted.__all__:
        assert hasattr(httpquoted, name)


def test_version_is_a_three_part_string() -> None:
    parts = httpquoted.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("httpquoted").joinpath("py.typed").is_file()


def test_the_error_is_a_value_error_with_reason_and_offset() -> None:
    error = httpquoted.QuotedStringError("bad", 3)
    assert isinstance(error, ValueError)
    assert (error.reason, error.offset, str(error)) == ("bad", 3, "bad at offset 3")


def test_options_are_keyword_only() -> None:
    for name in httpquoted.__all__:
        function = getattr(httpquoted, name)
        if name == "QuotedStringError":
            continue
        for parameter in inspect.signature(function).parameters.values():
            if parameter.default is not inspect.Parameter.empty and parameter.name != "start":
                assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (name, parameter)


def test_the_module_exposes_nothing_public_beyond_all() -> None:
    names = [name for name in dir(httpquoted) if not name.startswith("_")]
    assert sorted(names) == sorted(httpquoted.__all__)
