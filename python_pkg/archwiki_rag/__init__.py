"""Offline Arch Wiki corpus for the ``knowledge-rag`` MCP server.

The ``arch-wiki-docs`` package ships the whole ArchWiki as HTML under
``/usr/share/doc/arch-wiki/html/en``. ``knowledge-rag`` cannot index HTML --
its parser dispatch table only understands ``.md``, ``.txt``, ``.pdf`` and a
handful of code suffixes -- so this package converts each page to Markdown and
drops it into a dedicated knowledge-rag store.

Markdown specifically, not plain text: knowledge-rag chunks ``.md`` files with
a heading-aware splitter and everything else with a blind fixed-width one.
ArchWiki pages are heavily sectioned, so emitting real ``##``/``###`` headings
is what makes chunk boundaries land on section breaks instead of mid-sentence.

The other load-bearing detail is in :mod:`python_pkg.archwiki_rag.sync`: the
knowledge-rag incremental reindex decides a file is unchanged by comparing
mtime and size, not content. The wiki dump regenerates every file on each
release, so the converter must leave byte-identical pages untouched on disk or
every ``arch-wiki-docs`` upgrade would re-embed the entire corpus.
"""

from __future__ import annotations
