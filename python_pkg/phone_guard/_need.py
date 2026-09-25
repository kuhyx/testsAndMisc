"""The answer :mod:`classify` gives for one adb call."""

from __future__ import annotations

from dataclasses import dataclass

SCREEN = "screen"
WHOLE_PHONE = "whole-phone"


@dataclass(frozen=True)
class Need:
    """What one adb call needs: a lease scope, a block, or nothing."""

    scope: str | None = None  # SCREEN, WHOLE_PHONE, or "pkg:<name>"
    block: str | None = None  # why it may not run at all
    display: int | None = None  # the virtual display it targets, if any
    serial: str | None = None  # from ``-s``
