"""Convert an offline ArchWiki HTML page into RAG-friendly Markdown.

Pure functions over strings: nothing here touches the filesystem, so the whole
conversion is testable from an HTML fixture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

from python_pkg.archwiki_rag.constants import (
    CONTENT_ID,
    HASHED_STEM,
    LOCAL_HREF,
    STRIP_SELECTORS,
    WIKI_BASE_URL,
)

if TYPE_CHECKING:
    from pathlib import Path


def is_wiki_page(path: Path) -> bool:
    """Report whether a file in the dump is a real, indexable wiki page.

    Parameters:
    path (Path): Candidate file from the offline HTML tree.

    Returns:
    bool: True for ordinary pages, False for the md5-named stray non-English
        pages the dump generator leaves in the English tree.
    """
    return path.suffix == ".html" and not HASHED_STEM.match(path.stem)


def page_name(path: Path, source: Path) -> str:
    """Derive the wiki page name from a file's position in the dump.

    Subpages are stored in nested directories -- ``en/Systemd/User.html`` is
    the page ``Systemd/User`` -- so the name is the path relative to the tree
    root, not merely the filename stem.

    Parameters:
    path (Path): File such as ``.../en/Systemd/User.html``.
    source (Path): Root of the offline HTML tree.

    Returns:
    str: The page name, e.g. ``Systemd/User``.
    """
    return path.relative_to(source).with_suffix("").as_posix()


def wiki_url(page: str) -> str:
    """Build the upstream URL for a page name.

    Parameters:
    page (str): Page name such as ``Systemd/User``.

    Returns:
    str: Canonical https URL on wiki.archlinux.org.
    """
    return f"{WIKI_BASE_URL}{page}"


def extract_title(soup: BeautifulSoup, fallback: str) -> str:
    """Read the human-readable page title.

    Prefers the rendered ``<h1>`` heading, which carries the wiki's own
    capitalisation (``systemd``, not ``Systemd``).

    Parameters:
    soup (BeautifulSoup): Parsed page.
    fallback (str): Value to use when the page has no ``<h1>``.

    Returns:
    str: Page title.
    """
    heading = soup.find("h1")
    if heading is None:
        return fallback
    text = heading.get_text(strip=True)
    return text or fallback


def rewrite_links(content: Tag) -> None:
    """Rewrite relative page links to absolute wiki.archlinux.org URLs, in place.

    The dump cross-links pages as ``../en/Foo.html``, which is meaningless once
    a chunk is quoted back to the user. Absolute URLs make retrieved passages
    citable and let the reader follow references without the local tree.

    Parameters:
    content (Tag): Article body to mutate.
    """
    for anchor in content.find_all("a", href=True):
        match = LOCAL_HREF.match(str(anchor["href"]))
        if match is None:
            continue
        anchor["href"] = wiki_url(match["page"]) + (match["frag"] or "")


def strip_chrome(content: Tag) -> None:
    """Remove navigation and editing furniture from the article body, in place.

    Parameters:
    content (Tag): Article body to mutate.
    """
    for selector in STRIP_SELECTORS:
        for element in content.select(selector):
            element.decompose()


def html_to_markdown(html: str, page: str) -> str | None:
    """Render one wiki page as Markdown with a citable front-matter header.

    Parameters:
    html (str): Raw HTML of an offline wiki page.
    page (str): Page name used for the source URL and title fallback.

    Returns:
    str | None: Markdown document, or None when the page has no article body
        (malformed or placeholder files in the dump).
    """
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id=CONTENT_ID)
    if content is None:
        return None

    title = extract_title(soup, page)
    strip_chrome(content)
    rewrite_links(content)

    body = markdownify(str(content), heading_style="ATX").strip()

    # A single H1 plus a source line: the title gives the heading-aware chunker
    # a document-level anchor, and the URL rides along into every chunk's text
    # so retrieved passages can be attributed without a metadata lookup.
    header = f"# {title}\n\nSource: {wiki_url(page)}\n"
    return f"{header}\n{body}\n"
