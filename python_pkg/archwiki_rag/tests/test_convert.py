"""Tests for archwiki_rag.convert."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from python_pkg.archwiki_rag import convert

PAGE_HTML = """
<html><head><title>systemd - ArchWiki</title></head><body>
<h1 id="firstHeading">systemd</h1>
<div id="mw-content-text">
  <div class="toc">Contents</div>
  <span class="mw-editsection">[edit]</span>
  <script>tracking()</script>
  <h2>Basic usage</h2>
  <p>See <a href="../en/Systemd/User.html#Basic_setup">systemd/User</a> and
     <a href="../en/Udev.html">udev</a>.</p>
  <p>External <a href="https://systemd.io/">project page</a>.</p>
  <pre>systemctl status</pre>
</div>
<div id="catlinks">Categories</div>
</body></html>
"""


class TestIsWikiPage:
    def test_ordinary_page(self) -> None:
        assert convert.is_wiki_page(Path("/dump/en/Systemd.html"))

    def test_md5_named_stray_rejected(self) -> None:
        stray = Path("/dump/en/01973e61502a6abccee11d2419aae5e4.html")
        assert not convert.is_wiki_page(stray)

    def test_non_html_rejected(self) -> None:
        assert not convert.is_wiki_page(Path("/dump/en/ArchWikiOffline.css"))


class TestPageName:
    def test_top_level(self) -> None:
        source = Path("/dump/en")
        assert convert.page_name(source / "Systemd.html", source) == "Systemd"

    def test_subpage_keeps_hierarchy(self) -> None:
        source = Path("/dump/en")
        page = convert.page_name(source / "Systemd" / "User.html", source)
        assert page == "Systemd/User"


class TestWikiUrl:
    def test_builds_upstream_url(self) -> None:
        assert convert.wiki_url("Systemd/User") == (
            "https://wiki.archlinux.org/title/Systemd/User"
        )


class TestExtractTitle:
    def test_uses_h1(self) -> None:
        soup = BeautifulSoup("<h1>systemd</h1>", "html.parser")
        assert convert.extract_title(soup, "Systemd") == "systemd"

    def test_falls_back_without_h1(self) -> None:
        soup = BeautifulSoup("<p>no heading</p>", "html.parser")
        assert convert.extract_title(soup, "Systemd") == "Systemd"

    def test_falls_back_on_empty_h1(self) -> None:
        soup = BeautifulSoup("<h1>  </h1>", "html.parser")
        assert convert.extract_title(soup, "Systemd") == "Systemd"


def _rewritten_href(html: str) -> str:
    """Rewrite links in a one-anchor fragment and return the resulting href.

    Parameters:
    html (str): HTML fragment containing exactly one anchor.

    Returns:
    str: The anchor's href after rewriting.
    """
    soup = BeautifulSoup(html, "html.parser")
    convert.rewrite_links(soup)
    anchor = soup.a
    assert anchor is not None
    return str(anchor["href"])


class TestRewriteLinks:
    def test_local_link_becomes_absolute(self) -> None:
        href = _rewritten_href('<a href="../en/Udev.html">udev</a>')
        assert href == "https://wiki.archlinux.org/title/Udev"

    def test_fragment_is_preserved(self) -> None:
        href = _rewritten_href('<a href="../en/Systemd/User.html#Basic_setup">x</a>')
        assert href == "https://wiki.archlinux.org/title/Systemd/User#Basic_setup"

    def test_external_link_untouched(self) -> None:
        href = _rewritten_href('<a href="https://systemd.io/">p</a>')
        assert href == "https://systemd.io/"


class TestStripChrome:
    def test_removes_navigation_furniture(self) -> None:
        soup = BeautifulSoup(
            '<div><div class="toc">C</div><p>body</p><script>x()</script></div>',
            "html.parser",
        )
        convert.strip_chrome(soup)
        assert "toc" not in str(soup)
        assert "x()" not in str(soup)
        assert "body" in str(soup)


class TestHtmlToMarkdown:
    def test_returns_none_without_article_body(self) -> None:
        assert convert.html_to_markdown("<html><body>nope</body></html>", "X") is None

    def test_renders_header_and_body(self) -> None:
        out = convert.html_to_markdown(PAGE_HTML, "Systemd")
        assert out is not None
        assert out.startswith("# systemd\n")
        assert "Source: https://wiki.archlinux.org/title/Systemd" in out

    def test_uses_atx_headings_for_chunker(self) -> None:
        out = convert.html_to_markdown(PAGE_HTML, "Systemd")
        assert out is not None
        assert "## Basic usage" in out

    def test_strips_chrome_and_rewrites_links(self) -> None:
        out = convert.html_to_markdown(PAGE_HTML, "Systemd")
        assert out is not None
        assert "Contents" not in out
        assert "[edit]" not in out
        assert "https://wiki.archlinux.org/title/Systemd/User#Basic_setup" in out
        assert "../en/" not in out

    def test_ends_with_single_newline(self) -> None:
        out = convert.html_to_markdown(PAGE_HTML, "Systemd")
        assert out is not None
        assert out.endswith("\n")
        assert not out.endswith("\n\n")
