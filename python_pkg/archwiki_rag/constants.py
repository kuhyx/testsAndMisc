"""Filesystem paths, selectors and thresholds for the Arch Wiki RAG corpus."""

from __future__ import annotations

from pathlib import Path
import re

# Source: the offline HTML dump shipped by the `arch-wiki-docs` package.
# Only the English tree is indexed; the other languages roughly quadruple the
# corpus without adding information this system would ever be queried for.
WIKI_HTML_DIR = Path("/usr/share/doc/arch-wiki/html/en")

# Destination: a *dedicated* knowledge-rag store. Deliberately not the shared
# ~/.local/share/knowledge-rag one -- roughly 35k Arch chunks would dominate
# both the BM25 index and the embedding space of any other corpus kept there.
DEFAULT_STORE_DIR = Path.home() / ".local/share/knowledge-rag-archwiki"

# Layout knowledge-rag imposes on a store directory.
DOCUMENTS_SUBDIR = "documents"
DATA_SUBDIR = "data"

# Written by knowledge-rag's single-instance guard; first line is the pid.
LOCK_FILENAME = "knowledge-rag.lock"

# The knowledge-rag venv, which owns chromadb/fastembed. The reindex must run
# under this interpreter, not the testsAndMisc one.
KNOWLEDGE_RAG_PYTHON = Path.home() / ".local/share/uv/tools/knowledge-rag/bin/python"

LOADAVG_PATH = Path("/proc/loadavg")

# Embedding is CPU-bound, not GPU-bound: knowledge-rag ships the CPU-only
# `onnxruntime` build, whose execution providers are Azure and CPU -- there is
# no CUDA provider, so a VRAM check would never fire. The reindex saturates
# roughly every core for minutes, so the guard watches load average instead.
#
# Expressed per core, so it is meaningful on any machine. Above this the box is
# already working hard (a build, a game, a download) and an unattended reindex
# should wait rather than pile on.
LOAD_PER_CORE_THRESHOLD = 1.5

# MediaWiki's Vector skin wraps the article body in this element.
CONTENT_ID = "mw-content-text"

# Chrome that carries no information once the page is out of a browser.
STRIP_SELECTORS = (
    "#toc",
    ".toc",
    ".mw-editsection",
    ".mw-jump-link",
    ".navbox",
    ".printfooter",
    "#catlinks",
    "script",
    "style",
)

WIKI_BASE_URL = "https://wiki.archlinux.org/title/"

# A handful of files in en/ are named after an md5 digest rather than a page
# title; they are stray non-English pages (e.g. a Latvian "Main page") that the
# dump generator failed to file under its own language tree.
HASHED_STEM = re.compile(r"^[0-9a-f]{32}$")

# Local hrefs look like "../en/Systemd/User.html#Basic_setup". Capture the page
# path so it can be rewritten to a citable upstream URL.
LOCAL_HREF = re.compile(
    r"^(?:\.\./)*(?:[a-z]{2,3}(?:-[a-z]+)?/)?(?P<page>.+?)\.html(?P<frag>#.*)?$",
)
