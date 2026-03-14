#!/usr/bin/env python3
"""Split OBRONA_MAGISTERSKA_ODPOWIEDZI.md into per-question files.

Each file: pytanie_NN.md (or pytanie_NN_MM.md for dual-numbered like 13/27).
Placed in pytania/questions/ folder.
"""

from __future__ import annotations

import logging
from pathlib import Path
import re

SCRIPT_DIR = str(Path(__file__).resolve().parent)
SOURCE = str(Path(SCRIPT_DIR) / "OBRONA_MAGISTERSKA_ODPOWIEDZI.md")
OUT_DIR = str(Path(SCRIPT_DIR) / "questions")
Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

with Path(SOURCE).open(encoding="utf-8") as f:
    lines = f.readlines()

# Find all question boundaries
question_starts = []
for i, line in enumerate(lines):
    m = re.match(r"^## PYTANIE (\d+(/\d+)?):(.*)$", line)
    if m:
        raw_num = m.group(1)  # e.g. "13/27" or "1"
        title = m.group(3).strip()
        question_starts.append((i, raw_num, title))

_logger.info("Found %d questions", len(question_starts))

for idx, (start_line, raw_num, title) in enumerate(question_starts):
    # End = next question start or EOF
    if idx + 1 < len(question_starts):
        end_line = question_starts[idx + 1][0]
    else:
        end_line = len(lines)

    # Extract content, strip trailing \newpage and blank lines
    content_lines = lines[start_line:end_line]
    # Remove trailing \newpage and blank lines
    while content_lines and content_lines[-1].strip() in ("", "\\newpage"):
        content_lines.pop()
    # Add final newline
    content_lines.append("\n")

    # Build filename: pytanie_01.md, pytanie_13_27.md
    safe_num = raw_num.replace("/", "_")
    # Zero-pad single numbers for sorting
    parts = safe_num.split("_")
    padded = "_".join(p.zfill(2) for p in parts)
    filename = f"pytanie_{padded}.md"

    filepath = str(Path(OUT_DIR) / filename)
    with Path(filepath).open("w", encoding="utf-8") as f:
        f.writelines(content_lines)

    line_count = len(content_lines)
    _logger.info(
        "  %-30s  (%4d lines)  PYTANIE %s: %s",
        filename,
        line_count,
        raw_num,
        title,
    )

_logger.info("All files written to: %s", OUT_DIR)
