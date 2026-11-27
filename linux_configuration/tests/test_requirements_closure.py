"""Tests for check_requirements_sync.py --testpaths (the pytest import closure).

The tree mimics the repo: a package whose tests import a test-only library,
and a script directory whose tests load a sibling helper that imports a
library lazily. Both must be reported; a TYPE_CHECKING-only import must not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from _requirements_closure import import_closure
from check_requirements_sync import main

if TYPE_CHECKING:
    from pathlib import Path

_TESTPATHS = ["pkg", "lc/tests"]


def _tree(root: Path) -> None:
    """Write the fake repo under ``root``."""
    files = {
        "pkg/__init__.py": "",
        "pkg/core.py": "import requests\n",
        "pkg/tests/test_core.py": "import hyp\nfrom pkg import core\n",
        "lc/tests/test_tool.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    import typeonly\n"
            "import helper\n"
        ),
        "lc/tools/helper.py": "def run():\n    import lazydep\n",
        "lc/tools/unused.py": "import notreached\n",
    }
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_closure_follows_local_imports_and_skips_type_checking(
    tmp_path: Path,
) -> None:
    """Report test-only and transitive imports; skip unreached and typing-only."""
    _tree(tmp_path)
    assert import_closure(tmp_path, _TESTPATHS) == {"hyp", "lazydep", "requests"}


def test_main_fails_until_every_import_is_declared(tmp_path: Path) -> None:
    """Exit 1 while a closure import is undeclared, 0 once all are pinned."""
    _tree(tmp_path)
    reqs = tmp_path / "req.txt"
    reqs.write_text("requests==1\n", encoding="utf-8")
    argv = ["--root", str(tmp_path), "--requirements", "req.txt", "--testpaths"]
    assert main([*argv, *_TESTPATHS]) == 1
    reqs.write_text("requests==1\nhyp==1\nlazydep==1\n", encoding="utf-8")
    assert main([*argv, *_TESTPATHS]) == 0
