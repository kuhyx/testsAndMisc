"""Measure the real per-turn prefix by starting Claude Code and reading usage.

Disk sizes do not predict billed cost: deferred MCP schemas are absent while
their tool *names* are not, and skill bodies are summarised. The only honest
number comes from a real process start.

Two lessons are encoded as defaults here, both learned by getting them wrong:

* ``--strict-mcp-config`` suppresses project-scoped ``.mcp.json`` files, so an
  A/B run with it understates the baseline (~2,000 tokens/turn in one audit).
  Probes therefore run **non-strict** unless explicitly asked otherwise.
* A saving predicted from a synthetic config must be re-measured after the
  change actually lands. :func:`check_prediction` exists to fail loudly when the
  two disagree, because one audit predicted 6,122 and delivered 4,465.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
PROBE_PROMPT = "say ok"
PROBE_TIMEOUT = 300
# Fraction by which a predicted saving may miss the measured one before the
# prediction is treated as unreliable rather than merely imprecise.
PREDICTION_TOLERANCE = 0.2
PREFIX_KINDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


@dataclass(frozen=True)
class Probe:
    """One measured process start."""

    label: str
    prefix_tokens: int


def _prefix_from_usage(usage: dict) -> int:
    """Sum the token classes that make up the request prefix.

    Cache creation and cache read are alternatives — a cold start reports the
    prefix as creation, a warm one as read — so summing both is correct and
    stable across repeat runs.
    """
    return sum(usage.get(kind) or 0 for kind in PREFIX_KINDS)


def measure(
    label: str,
    *,
    cwd: Path | None = None,
    mcp_config: Path | None = None,
    strict: bool = False,
) -> Probe:
    """Start Claude Code once and report the prefix it billed.

    ``strict`` defaults to False on purpose; see the module docstring.
    """
    cmd = [str(CLAUDE_BIN), "-p", PROBE_PROMPT, "--output-format", "json"]
    if mcp_config is not None:
        cmd += ["--mcp-config", str(mcp_config)]
        if strict:
            cmd.append("--strict-mcp-config")
    result = subprocess.run(
        cmd,
        cwd=str(cwd or Path.home()),
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT,
        check=True,
    )
    usage = json.loads(result.stdout).get("usage") or {}
    return Probe(label, _prefix_from_usage(usage))


def check_prediction(
    predicted_saving: int, measured_saving: int, tolerance: float = PREDICTION_TOLERANCE
) -> str | None:
    """Return a warning when a predicted saving missed the measured one.

    Returns ``None`` when the prediction held, so callers can treat a truthy
    result as a gate failure.
    """
    if predicted_saving <= 0:
        return None
    drift = abs(measured_saving - predicted_saving) / predicted_saving
    if drift <= tolerance:
        return None
    return (
        f"prediction off by {drift:.0%}: predicted {predicted_saving:,} "
        f"tokens/turn, measured {measured_saving:,}"
    )


def weighted_pct(
    tokens_per_turn: int,
    turns: int,
    weighted_total: int,
    cache_read_weight: float = 0.1,
) -> float:
    """Convert a per-turn prefix saving into a share of weighted spend.

    Every lever must be quoted through this function. Prefix tokens are billed
    as cache reads, which carry a 0.1 weight, so a raw per-turn figure compared
    against a weighted headline overstates the saving by roughly 10x — a
    mistake made, and caught, in an earlier audit.
    """
    if weighted_total <= 0:
        return 0.0
    return 100.0 * tokens_per_turn * turns * cache_read_weight / weighted_total
