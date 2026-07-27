"""Test isolation for the /wsg/ grabber.

This package writes an index and tens of gigabytes of video into
``~/.local/share/wsg_grabber``. A test that escapes into the real directory
would corrupt live user data, so redirection is autouse and belt-and-braces:

1. ``Path.home`` is patched on the *class*, so it holds no matter whether a
   module wrote ``from pathlib import Path`` or ``import pathlib``.
2. ``HOME`` and ``XDG_DATA_HOME`` are redirected, catching anything that goes
   through ``os.environ`` or ``expanduser`` instead.
3. Every module reaches storage only through :mod:`python_pkg.wsg_grabber.paths`
   functions, which resolve on each call rather than at import.

``tests/test_paths.py`` adds a static check that no module captures a home
directory at import time, so layer 3 stays true as the package grows.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every storage location at a throwaway directory.

    No teardown is needed: ``monkeypatch`` unwinds both the environment and the
    ``Path.home`` patch when the test ends.

    Args:
        tmp_path: Per-test temporary directory supplied by pytest.
        monkeypatch: Patching helper, unwound automatically after the test.

    Returns:
        Path: The fake home directory backing this test.
    """
    home = tmp_path / "home"
    data_home = home / ".local" / "share"
    data_home.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))

    return home
