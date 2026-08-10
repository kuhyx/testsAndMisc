# archwiki_rag

Offline Arch Wiki corpus for the `knowledge-rag` MCP server. Gives Claude
semantic search across the whole ArchWiki without a network round-trip, so
questions can be asked by _symptom_ rather than by page title:

> why doesn't my systemd user unit see DISPLAY under i3

## Why this exists

The only Arch-specific MCP server in the wild
([`nihalxkumar/arch-mcp`](https://github.com/nihalxkumar/arch-mcp)) fetches wiki
pages over the network and bundles pacman install/remove/update, PKGBUILD
checks and system stats that duplicate the local `yay-mcp`. This package uses
the `arch-wiki-docs` dump that is already on disk instead, and does nothing but
search.

## Usage

```bash
# One-time setup: dependencies, corpus, MCP config, pacman hook.
./install.sh

# Manual refresh.
PYTHONPATH=~/testsAndMisc python3 -m python_pkg.archwiki_rag sync --reindex

# Query it.
claude-archwiki
```

Then, in the session, `search_knowledge("...")` against the `archwiki` server.

## Design notes

Three non-obvious constraints shaped this package. All three come from reading
the `knowledge-rag` source rather than its docs.

**Markdown, not text.** `knowledge-rag` chunks `.md` files with a heading-aware
splitter and everything else with a blind fixed-width one. ArchWiki pages are
heavily sectioned, so emitting real `##`/`###` headings is what makes chunk
boundaries land on section breaks instead of mid-sentence. HTML is not a
supported suffix at all, so conversion is mandatory regardless.

**Never rewrite an unchanged file.** The incremental reindex decides a document
is current by comparing stored mtime and size, _not_ content. `arch-wiki-docs`
regenerates all ~2500 files on every release, so writing unconditionally would
bump every mtime and re-embed the entire corpus on each upgrade. `sync.py`
compares rendered output against what is on disk and skips identical pages;
this is the single most load-bearing behaviour in the package, and
`test_sync.py` asserts it directly.

**Subpages are nested.** `Systemd/User` lives at `en/Systemd/User.html`, not
`en/Systemd_User.html`. A non-recursive glob silently misses 164 pages, many of
them the most useful ones. `iter_pages` uses `rglob` and the documents tree
mirrors the dump's layout.

## Store isolation

The corpus lives in its own store, `~/.local/share/knowledge-rag-archwiki`, not
the shared `~/.local/share/knowledge-rag`. Roughly 27k Arch chunks would
otherwise dominate both the BM25 index and the embedding space of any other
corpus kept there. `claude-rag` and `claude-archwiki` are separate sessions
against separate indexes.

## Refresh guards

The pacman hook fires unattended, so `reindex.py` refuses to run when either:

- a `claude-archwiki` session already holds the store's instance lock
  (`knowledge-rag`'s own lock is taken only by its `main()`, so importing the
  orchestrator directly would bypass it), or
- the machine is already under load (1-minute load average above 1.5 per core).

The load guard, not a GPU one: `knowledge-rag` ships the CPU-only
`onnxruntime` build, whose execution providers are `AzureExecutionProvider` and
`CPUExecutionProvider`. There is no CUDA provider, so despite the 3090 in this
box the embedding pass runs on the CPU and saturates roughly every core for
several minutes. A VRAM check would have looked reassuring and never fired.

Deferring is safe: the converted Markdown is already on disk, so the next run
picks up exactly where this one stopped.
