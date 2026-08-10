"""Convert the offline ArchWiki dump into a knowledge-rag documents directory.

The one rule that matters here: **never rewrite a file whose content did not
change.** knowledge-rag's incremental reindex decides a document is up to date
by comparing the stored mtime and size against the file on disk
(``server.py`` in the knowledge-rag package). The ``arch-wiki-docs`` dump
regenerates all ~2400 files on every release, so a converter that wrote
unconditionally would bump every mtime and force a full re-embed of the corpus
on each upgrade. Comparing rendered output against what is already on disk
turns that into a handful of pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from python_pkg.archwiki_rag.convert import html_to_markdown, is_wiki_page, page_name

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass(frozen=True)
class SyncResult:
    """Outcome of one conversion pass over the dump.

    Attributes:
    converted (int): Pages successfully rendered to Markdown.
    changed (int): Pages whose Markdown differed from what was on disk and so
        were written. Only these get re-embedded on the next reindex.
    skipped (int): Files ignored -- md5-named strays and pages with no body.
    """

    converted: int
    changed: int
    skipped: int


def iter_pages(source: Path) -> Iterator[Path]:
    """Yield indexable HTML pages from the dump, in a stable order.

    Walks recursively: subpages such as ``Systemd/User`` live in nested
    directories, and they are some of the most useful pages in the wiki.

    Parameters:
    source (Path): Directory holding the offline HTML tree.

    Yields:
    Path: Each real wiki page, sorted so runs are reproducible.
    """
    for path in sorted(source.rglob("*.html")):
        if is_wiki_page(path):
            yield path


def write_if_changed(destination: Path, text: str) -> bool:
    """Write ``text`` only when it differs from the file already on disk.

    Parameters:
    destination (Path): Target Markdown file.
    text (str): Rendered document.

    Returns:
    bool: True when the file was written, False when it was already identical.
    """
    if destination.exists() and destination.read_text(encoding="utf-8") == text:
        return False
    destination.write_text(text, encoding="utf-8")
    return True


def sync_pages(source: Path, documents_dir: Path) -> SyncResult:
    """Convert every page in the dump into the knowledge-rag documents directory.

    Parameters:
    source (Path): Offline HTML tree, e.g. ``/usr/share/doc/arch-wiki/html/en``.
    documents_dir (Path): knowledge-rag ``documents/`` directory to populate.

    Returns:
    SyncResult: Counts of converted, changed and skipped pages.
    """
    documents_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    changed = 0
    skipped = 0

    for path in sorted(source.rglob("*.html")):
        if not is_wiki_page(path):
            skipped += 1
            continue
        page = page_name(path, source)
        markdown = html_to_markdown(
            path.read_text(encoding="utf-8", errors="replace"), page
        )
        if markdown is None:
            skipped += 1
            continue
        converted += 1
        # Mirror the dump's directory layout; knowledge-rag walks documents/
        # recursively, so nesting costs nothing and keeps page names natural.
        destination = documents_dir / f"{page}.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if write_if_changed(destination, markdown):
            changed += 1

    return SyncResult(converted=converted, changed=changed, skipped=skipped)
