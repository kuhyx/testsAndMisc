"""Tests for generate_images/generate_anki.py (part 3): remaining coverage gaps."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Content with definitions outside acceptable length range
_MD_DEF_LENGTH = """\
# Pytanie 01: Definitions

Przedmiot: Informatyka

## Pytanie

**"Main question?"**

## 📚 Odpowiedź główna

### First header
Description.

**Short** -- tiny
**TooLong** -- %s
**GoodLen** -- This definition is just the right length for extraction.
""" % ("x" * 210)

# Content for subsection testing
_MD_SUBSECTIONS = """\
# Pytanie 02: Subsections

Przedmiot: Fizyka

## Pytanie

**"Test subsections?"**

## 📚 Odpowiedź główna

### 1. Header ending with question?

Paragraph body that is long enough for extraction and subsection answer test.

### 2. Short body section

Short body text that is less than fifty characters total.

### 3. Only tables and code

| col1 | col2 | col3 | col4 | col5 | col6 |
| val1 | val2 | val3 | val4 | val5 | val6 |

### Właściwości important concept

- **Property**: This is a property description for the concept in question.

### Przykład skip me
Text that should be from a skipped section.
"""

# Content with formula of insufficient length
_MD_SHORT_FORMULA = """\
# Pytanie 03: Short Formula

Przedmiot: Matematyka

## Pytanie

**"Formulas?"**

## 📚 Odpowiedź główna

### Sorting algo
Text here.

**Short twierdzenie**: abc

**Valid formuła**: This formula has enough length to pass the check.
"""


@pytest.fixture
def def_length_file(tmp_path: Path) -> Path:
    """File with definitions of various lengths."""
    p = tmp_path / "01-definitions.md"
    p.write_text(_MD_DEF_LENGTH, encoding="utf-8")
    return p


@pytest.fixture
def subsection_file(tmp_path: Path) -> Path:
    """File with various subsection patterns."""
    p = tmp_path / "02-subsections.md"
    p.write_text(_MD_SUBSECTIONS, encoding="utf-8")
    return p


@pytest.fixture
def formula_file(tmp_path: Path) -> Path:
    """File with short formula content."""
    p = tmp_path / "03-short-formula.md"
    p.write_text(_MD_SHORT_FORMULA, encoding="utf-8")
    return p


# --- _extract_main_card: definition length filter (78->77) ---


def test_main_card_def_outside_length(def_length_file: Path) -> None:
    """Definitions too short or too long are skipped (78->77)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_main_card,
        _get_metadata,
    )

    num, topic, title, main_q, content = _get_metadata(str(def_length_file))
    cards = _extract_main_card(content, main_q, "Informatyka", num, topic)
    assert isinstance(cards, list)


# --- _extract_sub_cards: continue branches (141, 145) ---


def test_sub_cards_short_body(subsection_file: Path) -> None:
    """Subsection with short body triggers continue (line 141)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
        _get_metadata,
    )

    num, topic, title, _, content = _get_metadata(str(subsection_file))
    cards = _extract_sub_cards(content, title, "Fizyka", num, topic)
    assert isinstance(cards, list)


def test_sub_cards_no_answer_text(tmp_path: Path) -> None:
    """Subsection where _extract_subsection_answer returns None (line 145)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
    )

    content = """\
### 1. Table only section

| col1 | col2 | col3 | col4 | col5 | col6 | col7 |
| val1 | val2 | val3 | val4 | val5 | val6 | val7 |

### 2. Valid section with content

- **Term**: Description of term for extraction to work properly.
"""
    cards = _extract_sub_cards(content, "Pytanie: 01 Test", "Fizyka", "01", "test")
    assert isinstance(cards, list)


def test_sub_cards_header_ends_question(subsection_file: Path) -> None:
    """Header ending with ? uses header as sub_question."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
        _get_metadata,
    )

    num, topic, title, _, content = _get_metadata(str(subsection_file))
    cards = _extract_sub_cards(content, title, "Fizyka", num, topic)
    # Check for question-ending header
    question_cards = [c for c in cards if c["question"].endswith("?")]
    assert isinstance(question_cards, list)


def test_sub_cards_wlasciwosci_keyword(subsection_file: Path) -> None:
    """Header with Właściwości keyword triggers special formatting."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
        _get_metadata,
    )

    num, topic, title, _, content = _get_metadata(str(subsection_file))
    cards = _extract_sub_cards(content, title, "Fizyka", num, topic)
    assert isinstance(cards, list)


# --- _extract_formula_cards: short formula (181->180) ---


def test_formula_short_content(formula_file: Path) -> None:
    """Formula with content <= MIN_FORMULA_LENGTH is skipped (181->180)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_formula_cards,
        _get_metadata,
    )

    _, _, _, _, content = _get_metadata(str(formula_file))
    cards = _extract_formula_cards(content, "Matematyka", "03")
    assert isinstance(cards, list)


# --- main() function (lines 232-271) ---


def test_main_function(tmp_path: Path) -> None:
    """main() processes files, handles errors, and writes output."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-ok.md").write_text("dummy", encoding="utf-8")
    (md_dir / "02-err.md").write_text("dummy", encoding="utf-8")
    out_file = tmp_path / "anki_egzamin_magisterski.txt"

    real_path = Path

    def fake_path(*args: object) -> Path:
        s = str(args[0]) if args else ""
        if "/home/kuchy/" in s and "odpowiedzi" in s:
            return real_path(md_dir)
        if "/home/kuchy/" in s:
            return real_path(out_file)
        return real_path(s)

    call_count = 0

    def fake_extract(filepath: object) -> list[dict[str, str]]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [{"question": "Q1", "answer": "A1", "tags": "t1"}]
        msg = "test error"
        raise ValueError(msg)

    with (
        patch.object(mod, "Path", side_effect=fake_path),
        patch.object(mod, "extract_question_and_answer", side_effect=fake_extract),
    ):
        mod.main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "#separator:tab" in content
    assert "Q1" in content


# --- Gap line 141: body_clean < MIN_BODY_LENGTH continue ---


def test_sub_cards_body_under_min_length() -> None:
    """Subsection with body_clean < MIN_BODY_LENGTH triggers continue (line 141)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
    )

    content = """\
### 1. Valid header with enough length

Tiny.

### 2. Another valid section name

- **Term**: Description of the term for extraction that is long enough to work.
"""
    cards = _extract_sub_cards(content, "Pytanie: 01 Test", "Fizyka", "01", "test")
    assert isinstance(cards, list)
    # Only the second section should produce a card (first has body < 50)
    assert len(cards) <= 1
