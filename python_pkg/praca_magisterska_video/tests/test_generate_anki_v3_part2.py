"""Tests for generate_images/generate_anki_v3.py (part 2): full coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

_SAMPLE_MD = """\
# Pytanie 01: Test Subject

Przedmiot: Informatyka

## Pytanie

**"What is the main concept?"**

## \U0001f4da Odpowied\u017a g\u0142\u00f3wna

### 1. First Concept

#### Definicja
This is the first concept definition here for thorough testing of coverage logic.

#### Charakterystyka
- **Feature1**: Description of feature one here for testing
- **Feature2**: Description of feature two here
- **Feature3**

Some extra paragraph here that is quite long and substantive with extra content \
for proper testing of the extraction logic and should be more than fifty chars.

### 2. Second Concept Short

Not enough body.

### Przyk\u0142ad - example section

This should be skipped because the header contains the Przyk\u0142ad keyword \
which is filtered out by the extraction logic in build concept cards.

### Some "quoted" header

This should also be skipped because there are quotes in header text \
and the extraction logic filters out headers with quote characters.

## \U0001f393 Pytania egzaminacyjne

### Q1: "What is a test question here?"
Odpowied\u017a:
The answer to this question is quite detailed.
It spans multiple lines for content.
```code block line```
| table line |
And includes more important information here.

### Q2: "Another question here?"
Odpowied\u017a:
Short.
"""

_AUTOMATA_MD = """\
# Pytanie 05: Automaty i j\u0119zyki

Przedmiot: Informatyka

## Pytanie

**"Co to jest automat sko\u0144czony i jakie j\u0119zyki rozpoznaje?"**

## \U0001f4da Odpowied\u017a g\u0142\u00f3wna

### 1. Automaty

Automat Sko\u0144czony (DFA/NFA) jest modelem obliczeniowym.
Rozpoznawana klasa j\u0119zyk\u00f3w
**Regular languages used in pattern matching and lexical analysis**

Automat ze Stosem (PDA) rozszerza automat sko\u0144czony o stos.
Rozpoznawana klasa j\u0119zyk\u00f3w
**Context-free languages used in parsing and syntax analysis**

Maszyna Turinga (TM) jest najpot\u0119\u017cniejszym modelem oblicze\u0144.
Rozpoznawana klasa j\u0119zyk\u00f3w
**Recursively enumerable languages and decidable language sets**
"""

_MINIMAL_MD = """\
# Just a title

No subject or question format here. No special sections at all.
"""

_DEF_BODY = """\
#### Definicja
This is a clear definition text spanning more than one line quite long.
It continues on the second line for the test purposes here.

#### Charakterystyka
- **Prop1**: Property description one text here
- **Prop2**: Property description two text
- **Prop3**
"""

_BULLET_ONLY_BODY = """\
Some introductory text that is ignored completely.

- **Alpha**: Description of alpha element here
- **Beta**: Description of beta element here
- **Gamma**
"""

_PLAIN_BODY = """\
This is a plain first paragraph without any structured content and it is long enough to be captured by regex.
"""

_PARA_ONLY_MD = """\
# Pytanie 03: Para Only

Przedmiot: Matematyka

## Pytanie

**"What is X?"**

## \U0001f4da Odpowied\u017a g\u0142\u00f3wna

### 1. Something Here

This is a substantive paragraph that is longer than fifty characters and provides \
meaningful content for testing paragraph extraction here today.
"""


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Markdown file matching extraction patterns."""
    p = tmp_path / "01-test-subject.md"
    p.write_text(_SAMPLE_MD, encoding="utf-8")
    return p


@pytest.fixture
def automata_file(tmp_path: Path) -> Path:
    """Markdown file with automata patterns."""
    p = tmp_path / "05-automaty.md"
    p.write_text(_AUTOMATA_MD, encoding="utf-8")
    return p


# --- clean_text ---


def test_clean_text_empty() -> None:
    """clean_text returns empty for empty input."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        clean_text,
    )

    assert clean_text("") == ""


def test_clean_text_formatting() -> None:
    """clean_text converts markdown to HTML."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        clean_text,
    )

    result = clean_text('**bold** *italic* "quote"\tand  spaces')
    assert "<b>bold</b>" in result
    assert "<i>italic</i>" in result
    assert "&quot;" in result
    assert "\t" not in result
    assert "  " not in result


# --- extract_real_answer ---


def test_extract_real_answer_subheaders() -> None:
    """extract_real_answer returns subheader content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_real_answer,
    )

    result = extract_real_answer(_SAMPLE_MD, "First Concept")
    assert result is not None
    assert "<b>" in result


def test_extract_real_answer_bullets() -> None:
    """extract_real_answer returns bullet content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_real_answer,
    )

    content = (
        "### Test Section\n- **Term1**: Description of term one here\n- **Term2**\n"
    )
    result = extract_real_answer(content, "Test Section")
    assert result is not None
    assert "Term1" in result
    assert "Term2" in result


def test_extract_real_answer_paragraphs() -> None:
    """extract_real_answer falls back to paragraphs."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_real_answer,
    )

    content = (
        "### Plain Section\n"
        "No bullet points here.\n\n"
        "This is a plain paragraph that is definitely longer than twenty characters "
        "for testing.\n\n"
        "Another paragraph also long enough for extraction purposes in tests.\n"
    )
    result = extract_real_answer(content, "Plain Section")
    assert result is not None


def test_extract_real_answer_no_match() -> None:
    """extract_real_answer returns None for missing section."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_real_answer,
    )

    assert extract_real_answer("no sections here", "Missing") is None


def test_extract_real_answer_empty_section() -> None:
    """extract_real_answer returns None for empty body."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_real_answer,
    )

    content = "### Empty\n\n### Next Section\n"
    assert extract_real_answer(content, "Empty") is None


# --- _read_file_metadata ---


def test_read_file_metadata_matching(sample_file: Path) -> None:
    """_read_file_metadata extracts metadata from matching filename."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _read_file_metadata,
    )

    content, base_tags, main_question = _read_file_metadata(sample_file)
    assert "pyt01" in base_tags
    assert "Informatyka" in base_tags
    assert main_question is not None
    assert "main concept" in main_question


def test_read_file_metadata_no_match(tmp_path: Path) -> None:
    """_read_file_metadata uses defaults for non-matching filename."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _read_file_metadata,
    )

    p = tmp_path / "readme.txt"
    p.write_text(_MINIMAL_MD, encoding="utf-8")
    content, base_tags, main_question = _read_file_metadata(p)
    assert "pyt00" in base_tags
    assert "Og\u00f3lne" in base_tags
    assert main_question is None


# --- _extract_automata_facts ---


def test_extract_automata_facts() -> None:
    """_extract_automata_facts finds all three automata types."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_automata_facts,
    )

    facts = _extract_automata_facts(_AUTOMATA_MD)
    assert len(facts) == 3
    assert any("FA" in f for f in facts)
    assert any("PDA" in f for f in facts)
    assert any("TM" in f for f in facts)


def test_extract_automata_facts_empty() -> None:
    """_extract_automata_facts returns empty for non-automata content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_automata_facts,
    )

    assert _extract_automata_facts("no automata here") == []


# --- _extract_generic_facts ---


def test_extract_generic_facts() -> None:
    """_extract_generic_facts finds definitions."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_generic_facts,
    )

    facts = _extract_generic_facts(_SAMPLE_MD)
    assert len(facts) >= 1


def test_extract_generic_facts_empty() -> None:
    """_extract_generic_facts returns empty for content without patterns."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_generic_facts,
    )

    assert _extract_generic_facts("no definitions") == []


# --- _extract_first_paragraphs ---


def test_extract_first_paragraphs() -> None:
    """_extract_first_paragraphs finds paragraphs from main answer."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_first_paragraphs,
    )

    paras = _extract_first_paragraphs(_SAMPLE_MD)
    assert isinstance(paras, list)


def test_extract_first_paragraphs_no_section() -> None:
    """_extract_first_paragraphs returns empty without main answer."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_first_paragraphs,
    )

    assert _extract_first_paragraphs("no main answer section") == []


# --- _build_main_card ---


def test_build_main_card_automata() -> None:
    """_build_main_card builds card using automata facts."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_main_card,
    )

    card = _build_main_card(
        _AUTOMATA_MD,
        "Co to jest automat sko\u0144czony?",
        "egzamin pyt05 Informatyka",
    )
    assert card is not None
    assert "pytanie_glowne" in card["tags"]


def test_build_main_card_automata_no_facts() -> None:
    """_build_main_card falls through to generic when automata finds nothing."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_main_card,
    )

    card = _build_main_card(
        _SAMPLE_MD,
        "Co to jest automat?",
        "tags",
    )
    assert card is not None


def test_build_main_card_generic() -> None:
    """_build_main_card builds card using generic facts."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_main_card,
    )

    card = _build_main_card(
        _SAMPLE_MD,
        "What is the main concept?",
        "egzamin pyt01 Informatyka",
    )
    assert card is not None


def test_build_main_card_first_paragraphs() -> None:
    """_build_main_card falls through to first paragraphs."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_main_card,
    )

    card = _build_main_card(_PARA_ONLY_MD, "What is X?", "tags")
    assert card is not None


def test_build_main_card_no_question() -> None:
    """_build_main_card returns None without main_question."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_main_card,
    )

    assert _build_main_card(_SAMPLE_MD, None, "tags") is None


def test_build_main_card_no_parts() -> None:
    """_build_main_card returns None when no content found."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_main_card,
    )

    assert _build_main_card("empty", "question?", "tags") is None


# --- _extract_section_content ---


def test_extract_section_content_definicja() -> None:
    """_extract_section_content finds Definicja and Charakterystyka."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_section_content,
    )

    lines = _extract_section_content(_DEF_BODY)
    assert len(lines) >= 2


def test_extract_section_content_bullets_only() -> None:
    """_extract_section_content falls back to generic bullets."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_section_content,
    )

    lines = _extract_section_content(_BULLET_ONLY_BODY)
    assert len(lines) >= 1
    assert any("Alpha" in line for line in lines)


def test_extract_section_content_plain() -> None:
    """_extract_section_content falls back to first paragraph."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_section_content,
    )

    lines = _extract_section_content(_PLAIN_BODY)
    assert len(lines) >= 1


def test_extract_section_content_empty() -> None:
    """_extract_section_content returns empty for no content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _extract_section_content,
    )

    assert _extract_section_content("") == []
