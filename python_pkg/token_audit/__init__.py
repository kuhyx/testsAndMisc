"""Measure what Claude Code sessions actually cost, from local transcripts.

Deterministic analysis with no model in the loop: the CLI parses
``~/.claude/projects/*/*.jsonl`` and ranks spend by project, tool, MCP server,
skill, subagent and session shape. Running the audit therefore costs nothing,
which is the point — an LLM summarising its own token usage would be the
expense it is trying to measure.

Usage::

    python3 -m token_audit            # rolling 7 days
    python3 -m token_audit --days 30
    python3 -m token_audit --json
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
