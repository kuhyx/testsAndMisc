"""Tests for generate_images/anki_generator.py (part 4): final branch gaps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Markdown with main question but no "📚 Odpowiedź główna" section
_MD_Q_NO_MAIN_ANSWER = """\
# Pytanie 14: No Main Answer

Przedmiot: Chemia

## Pytanie

**"Where is the main answer section?"**

## Some unrelated section

Random text here with no main answer heading at all.

### 1. Detail subsection here
Body that is long enough to pass the minimum body length threshold for testing.
"""


@pytest.fixture
def q_no_answer_file(tmp_path: Path) -> Path:
    """MD with main question but no 📚 Odpowiedź główna section."""
    p = tmp_path / "14-no-main-answer.md"
    p.write_text(_MD_Q_NO_MAIN_ANSWER, encoding="utf-8")
    return p


# --- Gap 121->119: kv entry duplicate causes `entry not in parts` to be False ---


def test_structured_content_kv_duplicate_skipped() -> None:
    """Duplicate kv entry already in parts is skipped (121->119 False)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    # No bullets (lines don't start with - or •), so parts stays empty.
    # Two identical kv entries: second is already in parts → skip branch.
    body = (
        "**Concept Alpha** -- description of alpha that is long enough here\n"
        "**Concept Alpha** -- description of alpha that is long enough here\n"
        "**Concept Beta** -- description of beta concept long enough too\n"
    )
    result = extract_structured_content(body)
    assert result is not None
    assert result.count("Concept Alpha") == 1
    assert "Concept Beta" in result


# --- Gap 151->163: extract_cards_better, answer_match is None ---


def test_cards_better_no_answer_section(q_no_answer_file: Path) -> None:
    """Main question exists but no answer section (151->163)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_better,
    )

    cards = extract_cards_better(str(q_no_answer_file))
    main_cards = [c for c in cards if "main" in c.get("tags", "")]
    assert main_cards == []


# --- Gap 179->168: detail section answer is None, loop continues ---


def test_cards_better_detail_answer_none(tmp_path: Path) -> None:
    """Detail section body passes length but content returns None (179->168)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_better,
    )

    md = """\
# Pytanie 15: Detail None

Przedmiot: Test

## Pytanie

**"Detail none test?"**

## 📚 Odpowiedź główna

Main answer content here that is long enough.

### Section with only code blocks and tables
```python
variable_long_enough_to_pass_body_length = True
another_variable_ensuring_over_fifty_chars = True
more_padding_content_added_for_safety_here = True
```

| col1 | col2 | col3 | col4 | col5 | col6 |
| val1 | val2 | val3 | val4 | val5 | val6 |
"""
    p = tmp_path / "15-detail-none.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_cards_better(str(p))
    detail_cards = [c for c in cards if "detail" in c.get("tags", "")]
    assert detail_cards == []


# --- Gap 203->222: extract_cards_basic, answer_match is None ---


def test_cards_basic_no_answer_section(q_no_answer_file: Path) -> None:
    """Main question exists but no answer section in basic (203->222)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_basic,
    )

    cards = extract_cards_basic(str(q_no_answer_file))
    main_cards = [c for c in cards if "main" in c.get("tags", "")]
    assert main_cards == []


# --- Gap 207->222: answer section exists but no ### headers ---


def test_cards_basic_no_headers_in_answer(tmp_path: Path) -> None:
    """Answer section exists but has no ### headers (207->222)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_basic,
    )

    md = """\
# Pytanie 16: No Headers

Przedmiot: Test

## Pytanie

**"No headers in answer?"**

## 📚 Odpowiedź główna

Just plain text without any level-3 headers in this section.
More content here but still no triple-hash headers at all.

## Next section

Something else entirely.
"""
    p = tmp_path / "16-no-headers.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_cards_basic(str(p))
    main_cards = [c for c in cards if "main" in c.get("tags", "")]
    assert main_cards == []
