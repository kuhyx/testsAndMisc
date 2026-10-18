"""Durable, zero-token store of Claude Code spend for the control-panel /tokens page.

``ingest`` walks transcripts (reusing token_audit's parser, dedup and prices)
into SQLite under ``~/data/token-dashboard/``; the dashboard only reads it.
"""
