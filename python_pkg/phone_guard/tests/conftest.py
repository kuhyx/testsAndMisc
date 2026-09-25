"""Keep every phone_guard test off the live lease and virtual-display state."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from python_pkg.phone_lease import lease as lease_mod

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect ~/.cache/phone-lease and /tmp/phone_vd into tmp_path."""
    monkeypatch.setenv("PHONE_VD_STATE_DIR", str(tmp_path / "phone_vd"))
    with patch.object(lease_mod, "LEASE_DIR", tmp_path / "leases"):
        yield tmp_path


def make_display(
    root: Path, serial: str, owner_dir: str, display: str, package: str
) -> None:
    """Write the state phone_vd.sh leaves for one running display."""
    state = root / "phone_vd" / serial / owner_dir
    state.mkdir(parents=True)
    (state / "display").write_text(display)
    (state / "sf").write_text("123")
    (state / "package").write_text(package)
