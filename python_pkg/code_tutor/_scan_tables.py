"""Which paths the analyzer walks past, and how it spots a function.

Split out of :mod:`python_pkg.code_tutor._analyzer` to keep it under the
250-line cap. Pure data tables with no collaborators, so nothing patches them.
"""

from __future__ import annotations

import re

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        "third_party",
        ".venv",
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
    }
)
_SKIP_SUFFIXES: frozenset[str] = frozenset(
    {
        ".geojson",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".webp",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".bin",
    }
)
_OTHER_LANGS: frozenset[str] = frozenset(
    {".js", ".ts", ".go", ".rs", ".c", ".cpp", ".dart"}
)

# Matches leading keyword(s) followed by an identifier and opening paren.
_FUNCTION_RE: re.Pattern[str] = re.compile(
    r"^[ \t]*(?:(?:pub(?:lic)?|priv(?:ate)?|prot(?:ected)?|static|async)\s+)*"
    r"(?:def|function|fn|func|void|int|float|bool|string)\s+(\w+)\s*\(",
    re.MULTILINE,
)
