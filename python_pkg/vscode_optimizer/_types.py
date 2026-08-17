"""Detected hardware, proposed changes, and the VS Code installations found.

These three dataclasses are the vocabulary the other modules share, kept
apart from them so nothing has to import a sibling just to name a type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class _Hw:
    """Detected system hardware."""

    cpu_model: str = "Unknown"
    cpu_physical_cores: int = 1
    cpu_logical_cores: int = 1
    cpu_max_mhz: float = 0.0
    ram_total_mb: int = 0
    gpu_vendor: str = "Unknown"
    gpu_model: str = "Unknown"
    gpu_vram_mb: int = 0
    disk_type: str = "unknown"


@dataclass
class _Opt:
    """Single proposed change."""

    key: str
    value: object
    reason: str
    current: object = None


@dataclass
class _Variant:
    """A VS Code installation."""

    name: str
    settings: Path
    flags: Path
    binary: str
