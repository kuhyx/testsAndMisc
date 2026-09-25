"""``python3 -m python_pkg.phone_guard``: the PreToolUse hook entry point."""

from __future__ import annotations

import sys

from python_pkg.phone_guard.hook import main

if __name__ == "__main__":
    sys.exit(main())
