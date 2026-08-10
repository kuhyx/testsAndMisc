"""Tests for archwiki_rag._reindex_entry.

The entry point normally runs under the knowledge-rag interpreter, where
``mcp_server`` is importable. Here a stub module is injected into
``sys.modules`` so the three exit paths can be exercised in-process.
"""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest

from python_pkg.archwiki_rag import _reindex_entry

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def fake_mcp_server() -> Iterator[MagicMock]:
    """Install a stub ``mcp_server.server`` module for the duration of a test.

    Yields:
    MagicMock: The stubbed ``get_orchestrator`` callable.
    """
    package = types.ModuleType("mcp_server")
    server = types.ModuleType("mcp_server.server")
    get_orchestrator = MagicMock()
    server.get_orchestrator = get_orchestrator
    package.server = server

    sys.modules["mcp_server"] = package
    sys.modules["mcp_server.server"] = server
    try:
        yield get_orchestrator
    finally:
        del sys.modules["mcp_server.server"]
        del sys.modules["mcp_server"]


class TestMain:
    def test_reports_missing_knowledge_rag(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # A None entry in sys.modules makes `import` raise ImportError, which
        # is exactly what happens for real when this module runs outside the
        # knowledge-rag venv.
        sys.modules["mcp_server"] = cast("types.ModuleType", None)
        try:
            assert _reindex_entry.main() == 1
        finally:
            del sys.modules["mcp_server"]

        assert "not importable" in capsys.readouterr().err

    def test_reports_reindex_failure(
        self,
        fake_mcp_server: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake_mcp_server.return_value.reindex_all.side_effect = RuntimeError("chroma")

        # A backend failure is translated into a non-zero exit rather than a
        # traceback, so the subprocess caller sees a clean exit code.
        with pytest.raises(SystemExit) as excinfo:
            _reindex_entry.main()

        assert excinfo.value.code == 1
        assert "reindex failed: chroma" in capsys.readouterr().err

    def test_success_reports_stats(
        self,
        fake_mcp_server: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake_mcp_server.return_value.reindex_all.return_value = {"indexed": 7}

        assert _reindex_entry.main() == 0
        assert "reindex complete" in capsys.readouterr().out
