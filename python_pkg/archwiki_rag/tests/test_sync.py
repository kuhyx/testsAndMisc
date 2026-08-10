"""Tests for archwiki_rag.sync."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.archwiki_rag import sync

if TYPE_CHECKING:
    from pathlib import Path

PAGE = """
<html><h1>{title}</h1>
<div id="mw-content-text"><h2>Body</h2><p>{body}</p></div>
</html>
"""

NO_BODY = "<html><body><p>placeholder</p></body></html>"


def _write_page(path: Path, title: str, body: str = "text") -> None:
    """Write a minimal wiki page fixture.

    Parameters:
    path (Path): Destination HTML file.
    title (str): Page heading.
    body (str): Paragraph content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(title=title, body=body), encoding="utf-8")


class TestIterPages:
    def test_skips_strays_and_finds_subpages(self, tmp_path: Path) -> None:
        _write_page(tmp_path / "Systemd.html", "systemd")
        _write_page(tmp_path / "Systemd" / "User.html", "systemd/User")
        (tmp_path / f"{'a' * 32}.html").write_text("stray", encoding="utf-8")

        found = sorted(p.name for p in sync.iter_pages(tmp_path))
        assert found == ["Systemd.html", "User.html"]


class TestWriteIfChanged:
    def test_writes_new_file(self, tmp_path: Path) -> None:
        target = tmp_path / "a.md"
        assert sync.write_if_changed(target, "hello") is True
        assert target.read_text(encoding="utf-8") == "hello"

    def test_rewrites_when_content_differs(self, tmp_path: Path) -> None:
        target = tmp_path / "a.md"
        target.write_text("old", encoding="utf-8")
        assert sync.write_if_changed(target, "new") is True
        assert target.read_text(encoding="utf-8") == "new"

    def test_leaves_identical_file_untouched(self, tmp_path: Path) -> None:
        target = tmp_path / "a.md"
        target.write_text("same", encoding="utf-8")
        before = target.stat().st_mtime_ns

        assert sync.write_if_changed(target, "same") is False
        # The whole incremental-reindex design rests on this: knowledge-rag
        # compares mtime and size, so an unchanged page must not be touched.
        assert target.stat().st_mtime_ns == before


class TestSyncPages:
    def test_counts_converted_changed_and_skipped(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        _write_page(source / "Systemd.html", "systemd")
        _write_page(source / "Systemd" / "User.html", "systemd/User")
        (source / f"{'b' * 32}.html").write_text("stray", encoding="utf-8")
        (source / "Broken.html").write_text(NO_BODY, encoding="utf-8")

        result = sync.sync_pages(source, tmp_path / "documents")

        assert result.converted == 2
        assert result.changed == 2
        assert result.skipped == 2

    def test_preserves_subpage_hierarchy(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        _write_page(source / "Systemd" / "User.html", "systemd/User")
        documents = tmp_path / "documents"

        sync.sync_pages(source, documents)

        page = documents / "Systemd" / "User.md"
        assert page.exists()
        assert "https://wiki.archlinux.org/title/Systemd/User" in page.read_text(
            encoding="utf-8",
        )

    def test_second_run_changes_nothing(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        _write_page(source / "Systemd.html", "systemd")
        documents = tmp_path / "documents"

        sync.sync_pages(source, documents)
        mtimes = {p: p.stat().st_mtime_ns for p in documents.rglob("*.md")}
        second = sync.sync_pages(source, documents)

        assert second.changed == 0
        assert all(p.stat().st_mtime_ns == m for p, m in mtimes.items())

    def test_edited_page_is_rewritten(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        _write_page(source / "Systemd.html", "systemd", body="first")
        documents = tmp_path / "documents"
        sync.sync_pages(source, documents)

        _write_page(source / "Systemd.html", "systemd", body="second")
        result = sync.sync_pages(source, documents)

        assert result.changed == 1
        assert "second" in (documents / "Systemd.md").read_text(encoding="utf-8")

    def test_creates_documents_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        source.mkdir()
        documents = tmp_path / "nested" / "documents"

        result = sync.sync_pages(source, documents)

        assert documents.is_dir()
        assert result == sync.SyncResult(converted=0, changed=0, skipped=0)
