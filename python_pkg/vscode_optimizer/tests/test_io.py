"""Tests for the filesystem layer: variant discovery, the JSONC parser,
backups, and the settings/flags readers and writers.

These use real files under ``tmp_path``. Nothing in this module may resolve a
path inside the running user's real ``~/.config``.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import pytest

from python_pkg.vscode_optimizer import _optimize as opt

if TYPE_CHECKING:
    from pathlib import Path


# --------------------------------------------------------------------------- #
# _parse_jsonc
# --------------------------------------------------------------------------- #
def test_parse_jsonc_reads_plain_json() -> None:
    """The parser is a superset of JSON."""
    assert opt._parse_jsonc('{"a": 1}') == {"a": 1}


def test_parse_jsonc_strips_line_and_block_comments() -> None:
    """Both VS Code comment styles are removed before parsing."""
    text = """
    {
        // a line comment
        "a": 1, /* an inline block */
        /* a
           multi-line block */
        "b": 2
    }
    """

    assert opt._parse_jsonc(text) == {"a": 1, "b": 2}


def test_parse_jsonc_keeps_comment_markers_inside_strings() -> None:
    """A // or /* inside a string literal is data, not a comment."""
    text = '{"url": "https://example.com/*x*/", "path": "// not a comment"}'

    assert opt._parse_jsonc(text) == {
        "url": "https://example.com/*x*/",
        "path": "// not a comment",
    }


def test_parse_jsonc_handles_escaped_quotes_in_strings() -> None:
    """A backslash-escaped quote does not end the string."""
    assert opt._parse_jsonc(r'{"a": "he said \"hi\""}') == {"a": 'he said "hi"'}


def test_parse_jsonc_drops_trailing_commas() -> None:
    """Trailing commas are legal in JSONC, before both } and ]."""
    assert opt._parse_jsonc('{"a": [1, 2,], "b": 3,}') == {"a": [1, 2], "b": 3}


def test_parse_jsonc_treats_an_empty_document_as_no_settings() -> None:
    """A blank or comment-only file parses to an empty mapping, not an error."""
    assert opt._parse_jsonc("") == {}
    assert opt._parse_jsonc("   \n\t ") == {}
    assert opt._parse_jsonc("// nothing but a comment") == {}


def test_parse_jsonc_tolerates_a_comment_without_a_trailing_newline() -> None:
    """A line comment running to end-of-file terminates cleanly."""
    assert opt._parse_jsonc('{"a": 1}\n// trailing') == {"a": 1}


def test_parse_jsonc_tolerates_an_unterminated_block_comment() -> None:
    """An unclosed /* swallows the rest of the file rather than looping."""
    assert opt._parse_jsonc('{"a": 1}\n/* never closed') == {"a": 1}


def test_parse_jsonc_tolerates_an_unterminated_string() -> None:
    """An unclosed quote consumes to end-of-input and then fails to parse."""
    with pytest.raises(json.JSONDecodeError):
        opt._parse_jsonc('{"a": "unterminated')


# --------------------------------------------------------------------------- #
# _discover_variants
# --------------------------------------------------------------------------- #
def test_discover_variants_finds_an_installation_by_its_settings_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A settings.json on disk is enough, even with no binary on PATH."""
    settings = tmp_path / ".config" / "VSCodium" / "User" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")
    monkeypatch.setattr(opt.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(shutil, "which", lambda _b: None)

    found = opt._discover_variants()

    assert [v.name for v in found] == ["VSCodium"]
    assert found[0].settings == settings


def test_discover_variants_finds_an_installation_by_its_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A binary on PATH counts even before the settings file exists."""
    monkeypatch.setattr(opt.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(
        shutil, "which", lambda b: "/usr/bin/code" if b == "code" else None
    )

    found = opt._discover_variants()

    assert [v.name for v in found] == ["VS Code (stable)"]
    assert found[0].flags == tmp_path / ".config" / "code-flags.conf"


def test_discover_variants_returns_nothing_when_no_editor_is_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A machine with no VS Code variant yields an empty list."""
    monkeypatch.setattr(opt.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(shutil, "which", lambda _b: None)

    assert opt._discover_variants() == []


def test_discover_variants_finds_every_installed_variant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """All three known variants can coexist."""
    monkeypatch.setattr(opt.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(shutil, "which", lambda _b: "/usr/bin/x")

    assert len(opt._discover_variants()) == 3


# --------------------------------------------------------------------------- #
# _backup
# --------------------------------------------------------------------------- #
def test_backup_copies_the_file_and_returns_the_destination(tmp_path: Path) -> None:
    """The backup keeps the original content and leaves the source in place."""
    src = tmp_path / "settings.json"
    src.write_text('{"a": 1}')

    dst = opt._backup(src)

    assert dst is not None
    assert dst.read_text() == '{"a": 1}'
    assert src.exists()
    assert dst.name.endswith(".bak")


def test_backup_of_a_missing_file_is_a_no_op(tmp_path: Path) -> None:
    """Nothing to back up is not an error."""
    assert opt._backup(tmp_path / "absent.json") is None


# --------------------------------------------------------------------------- #
# settings and flags round-trips
# --------------------------------------------------------------------------- #
def test_read_settings_parses_jsonc_from_disk(tmp_path: Path) -> None:
    """Comments in a real settings.json are tolerated."""
    path = tmp_path / "settings.json"
    path.write_text('{\n  // comment\n  "editor.fontSize": 14\n}')

    assert opt._read_settings(path) == {"editor.fontSize": 14}


def test_read_settings_of_a_missing_file_is_empty(tmp_path: Path) -> None:
    """A variant with no settings yet reads as no settings."""
    assert opt._read_settings(tmp_path / "absent.json") == {}


def test_write_settings_merges_the_plan_over_the_current_values(
    tmp_path: Path,
) -> None:
    """Proposed values win; untouched user settings survive."""
    path = tmp_path / "nested" / "settings.json"
    current: dict[str, object] = {"editor.fontSize": 14, "a": 1}
    opts = [
        opt._Opt("a", 2, "reason"),
        opt._Opt(key="b", value=True, reason="reason"),
    ]

    opt._write_settings(path, current, opts)

    assert json.loads(path.read_text()) == {"editor.fontSize": 14, "a": 2, "b": True}


def test_write_settings_creates_the_parent_directory(tmp_path: Path) -> None:
    """A brand-new variant directory is created rather than failing."""
    path = tmp_path / "deep" / "nested" / "settings.json"

    opt._write_settings(path, {}, [])

    assert path.exists()


def test_read_flags_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    """The flags file is a plain list, with # comments."""
    path = tmp_path / "code-flags.conf"
    path.write_text(
        "# a comment\n\n  --enable-gpu-rasterization  \n--enable-zero-copy\n"
    )

    assert opt._read_flags(path) == [
        "--enable-gpu-rasterization",
        "--enable-zero-copy",
    ]


def test_read_flags_of_a_missing_file_is_empty(tmp_path: Path) -> None:
    """No flags file means no existing flags."""
    assert opt._read_flags(tmp_path / "absent.conf") == []


def test_write_flags_round_trips_through_read_flags(tmp_path: Path) -> None:
    """What is written is what is read back."""
    path = tmp_path / "code-flags.conf"
    flags = ["--enable-gpu-rasterization", "--ignore-gpu-blocklist"]

    opt._write_flags(path, flags)

    assert opt._read_flags(path) == flags
    assert path.read_text().endswith("\n")
