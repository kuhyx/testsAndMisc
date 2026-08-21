"""Tests for meta/scripts/extract_shell_functions.py.

The extractor is what every 250-line-cap split runs through, and its failure
mode is silent: a function form it does not recognise is simply left behind in
the entry script while the tool still reports success. That is how 17 of the
30 functions in pacman_wrapper.sh were nearly missed — the original pattern
matched only `name() {` and not bash's `function name() {` spelling.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "meta" / "scripts" / "extract_shell_functions.py"


def _load() -> ModuleType:
    """Import the script by path; it lives outside any importable package."""
    spec = importlib.util.spec_from_file_location("extract_shell_functions", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="esf", scope="module")
def _esf() -> ModuleType:
    return _load()


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        # Both spellings bash accepts, with and without whitespace variants.
        ("foo() {", "foo"),
        ("foo(){", "foo"),
        ("foo ()  {", "foo"),
        ("function foo() {", "foo"),
        ("function foo(){", "foo"),
        # The keyword form may omit the parentheses entirely.
        ("function foo {", "foo"),
        ("_leading_underscore() {", "_leading_underscore"),
        ("name2() {", "name2"),
    ],
)
def test_recognises_every_function_spelling(
    esf: ModuleType, line: str, expected: str
) -> None:
    """Every form bash accepts must be detected, and named correctly."""
    match = esf._FUNC_RE.match(line)
    assert match is not None, f"{line!r} was not recognised as a function"
    name = match.group("kwname") or match.group("name")
    assert name == expected


@pytest.mark.parametrize(
    "line",
    [
        # Indented definitions are not top level.
        "  indented() {",
        "\tindented() {",
        # Brace groups and control flow must never be swept into a library:
        # without the mandatory (), these would match and the extractor would
        # move non-function code.
        "while true; do {",
        "if x {",
        "{",
        "}",
        # A commented-out definition is not a definition.
        "# foo() {",
        # A call is not a definition.
        "foo()",
        "",
    ],
)
def test_ignores_everything_that_is_not_a_top_level_function(
    esf: ModuleType, line: str
) -> None:
    assert esf._FUNC_RE.match(line) is None, (
        f"{line!r} was wrongly treated as a function"
    )


def test_brace_matching_spans_the_whole_body(esf: ModuleType) -> None:
    """A function block must end at its own closing brace, not the first one."""
    lines = [
        "function outer() {",
        "\tif true; then",
        "\t\techo nested",
        "\tfi",
        "\tcase $x in",
        "\ta) echo a ;;",
        "\tesac",
        "}",
        "",
        "after() {",
        "\techo after",
        "}",
    ]
    blocks = esf.find_function_blocks(lines)
    assert [name for _, _, name in blocks] == ["outer", "after"]
    start, end, _ = blocks[0]
    assert (start, end) == (0, 7)


def test_single_line_function_closes_on_its_own_line(esf: ModuleType) -> None:
    """`name() { ...; }` opens and closes on one line."""
    blocks = esf.find_function_blocks(["logg() { printf '%s\\n' \"$*\"; }", "echo hi"])
    assert [name for _, _, name in blocks] == ["logg"]
    start, end, _ = blocks[0]
    assert start == end == 0


def test_detects_both_spellings_in_one_file(esf: ModuleType) -> None:
    """The regression that motivated these tests: a file mixing both forms."""
    lines = [
        "#!/bin/bash",
        "plain() {",
        "\techo plain",
        "}",
        "",
        "function keyword() {",
        "\techo keyword",
        "}",
        "",
        "function no_parens {",
        "\techo no_parens",
        "}",
    ]
    names = [name for _, _, name in esf.find_function_blocks(lines)]
    assert names == ["plain", "keyword", "no_parens"]
