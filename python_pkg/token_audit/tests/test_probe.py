"""Tests for the prefix probe and its prediction gate."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_audit import probe

if TYPE_CHECKING:
    from pathlib import Path


def test_prefix_sums_cold_start() -> None:
    """A cold start reports the prefix as cache creation."""
    usage = {
        "input_tokens": 2,
        "cache_creation_input_tokens": 46434,
        "cache_read_input_tokens": 0,
    }
    assert probe._prefix_from_usage(usage) == 46436


def test_prefix_sums_warm_start() -> None:
    """A warm start reports the same prefix as cache read."""
    usage = {"input_tokens": 2, "cache_read_input_tokens": 46434}
    assert probe._prefix_from_usage(usage) == 46436


def test_prefix_handles_missing_and_null() -> None:
    """Absent or null token classes count as zero."""
    assert probe._prefix_from_usage({}) == 0
    assert probe._prefix_from_usage({"input_tokens": None}) == 0


def test_prediction_within_tolerance_passes() -> None:
    """A prediction close to the measurement is not flagged."""
    assert probe.check_prediction(1000, 900) is None


def test_prediction_beyond_tolerance_is_flagged() -> None:
    """The 6,122-vs-4,465 miss from a real audit must fail the gate."""
    warning = probe.check_prediction(6122, 4465)
    assert warning is not None
    assert "27%" in warning


def test_prediction_ignores_nonpositive() -> None:
    """No prediction means nothing to check."""
    assert probe.check_prediction(0, 500) is None


def test_weighted_pct_applies_cache_read_weight() -> None:
    """Prefix savings are billed as cache reads, at weight 0.1."""
    assert probe.weighted_pct(4465, 44311, 1230346533) == pytest.approx(1.608, abs=0.01)


def test_weighted_pct_guards_zero_total() -> None:
    """An empty week cannot divide by zero."""
    assert probe.weighted_pct(100, 10, 0) == 0.0


def test_measure_runs_non_strict_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Strict mode hides project .mcp.json, so it must be opt-in."""
    seen: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(
            cmd, 0, json.dumps({"usage": {"input_tokens": 5}}), ""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = probe.measure("base", mcp_config=tmp_path / "x.json")
    assert "--strict-mcp-config" not in seen["cmd"]
    assert result.prefix_tokens == 5


def test_measure_can_opt_into_strict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Strict mode is still reachable when deliberately requested."""
    seen: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"usage": {}}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    probe.measure("strict", mcp_config=tmp_path / "x.json", strict=True)
    assert "--strict-mcp-config" in seen["cmd"]


def test_measure_without_mcp_config_omits_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The plain probe passes no MCP flags at all."""
    seen: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"usage": {}}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    probe.measure("plain")
    assert "--mcp-config" not in seen["cmd"]
