"""``python -m python_pkg.swap_bench`` entry point."""

from __future__ import annotations

import sys

from python_pkg.swap_bench import cli

sys.exit(cli.main())
