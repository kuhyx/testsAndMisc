"""Run the VS Code optimizer as ``python3 -m python_pkg.vscode_optimizer``.

The optimizer used to live at ``meta/scripts/optimize_vscode.py`` and was run
by path. It moved under ``python_pkg/`` so the repo-wide coverage gate
(``--cov=python_pkg``, ``fail_under = 100``) measures it; running it by path
no longer works, because ``sys.path[0]`` would be the script's own directory
rather than the repo root.
"""

from __future__ import annotations

from python_pkg.vscode_optimizer._optimize import main

if __name__ == "__main__":
    main()
