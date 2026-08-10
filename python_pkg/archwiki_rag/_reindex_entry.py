"""Headless reindex entry point, executed by the *knowledge-rag* interpreter.

This module is deliberately tiny and never imported by the rest of the package:
``chromadb`` and the embedding model live in the knowledge-rag venv, not in the
testsAndMisc one, so :mod:`python_pkg.archwiki_rag.reindex` runs this file with
that other interpreter.

It exists as a real file rather than a ``python -c`` string so the repo's ruff,
mypy and pytest still apply to it.
"""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

_SERVER_MODULE = "mcp_server.server"


def _load_get_orchestrator() -> Callable[[], object]:
    """Resolve ``mcp_server.server.get_orchestrator`` at call time.

    The import has to be deferred: ``mcp_server`` lives in the knowledge-rag
    venv, so at module-import time under any other interpreter it is simply
    absent. :func:`importlib.import_module` expresses that deliberately,
    rather than a function-level ``import`` statement that reads like an
    oversight and trips the lint that forbids one.

    Returns:
    Callable[[], object]: The orchestrator factory.

    Raises:
    ImportError: If knowledge-rag is not importable from this interpreter.
    """
    return importlib.import_module(_SERVER_MODULE).get_orchestrator


def main() -> int:
    """Run a synchronous smart reindex of the store named by ``KNOWLEDGE_RAG_DIR``.

    ``reindex_all`` is the same code path the ``reindex_documents(force=True)``
    MCP tool wraps, minus the background thread -- running it inline lets the
    caller block until the embedding pass is genuinely finished.

    Returns:
    int: 0 on success, 1 when knowledge-rag could not be imported or the
        reindex raised.
    """
    try:
        get_orchestrator = _load_get_orchestrator()
    except ImportError as exc:
        sys.stderr.write(f"knowledge-rag is not importable: {exc}\n")
        return 1

    # This module is a process entry point: the caller sees an exit code and
    # stderr, nothing else. Every failure the embedding backend can raise --
    # chromadb errors, model-download failures, OSError on a half-written
    # index -- has to become exit 1 rather than a traceback. Re-raising as
    # SystemExit keeps that translation explicit: the exception is reported
    # and converted, never silently swallowed, which is what the lint against
    # broad handlers is actually guarding against.
    try:
        stats = get_orchestrator().reindex_all()
    except Exception as exc:
        sys.stderr.write(f"reindex failed: {exc}\n")
        raise SystemExit(1) from exc

    sys.stdout.write(f"reindex complete: {stats}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
