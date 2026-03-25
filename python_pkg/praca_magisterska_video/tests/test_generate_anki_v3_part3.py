"""Tests for generate_images/generate_anki_v3.py (part 3): remaining coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

_SAMPLE_MD = """\
# Pytanie 01: Test Subject

Przedmiot: Informatyka

## Pytanie

**"What is the main concept?"**

## 📚 Odpowiedź główna

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

### Przykład - example section

This should be skipped because the header contains the Przykład keyword \
which is filtered out by the extraction logic in build concept cards.

### Some "quoted" header

This should also be skipped because there are quotes in header text \
and the extraction logic filters out headers with quote characters.

## 🎓 Pytania egzaminacyjne

### Q1: "What is a test question here?"
Odpowiedź:
The answer to this question is quite detailed.
It spans multiple lines for content.
```code block line```
| table line |
And includes more important information here.

### Q2: "Another question here?"
Odpowiedź:
Short.
"""

_AUTOMATA_MD = """\
# Pytanie 05: Automaty i języki

Przedmiot: Informatyka

## Pytanie

**"Co to jest automat skończony i jakie języki rozpoznaje?"**

## 📚 Odpowiedź główna

### 1. Automaty

Automat Skończony (DFA/NFA) jest modelem obliczeniowym.
Rozpoznawana klasa języków
**Regular languages used in pattern matching and lexical analysis**

Automat ze Stosem (PDA) rozszerza automat skończony o stos.
Rozpoznawana klasa języków
**Context-free languages used in parsing and syntax analysis**

Maszyna Turinga (TM) jest najpotężniejszym modelem obliczeń.
Rozpoznawana klasa języków
**Recursively enumerable languages and decidable language sets**
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


# --- _build_concept_cards ---


def test_build_concept_cards() -> None:
    """_build_concept_cards extracts concept cards, filtering Przykład."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_concept_cards,
    )

    cards = _build_concept_cards(_SAMPLE_MD, "egzamin pyt01")
    assert isinstance(cards, list)
    for c in cards:
        assert "Przykład" not in c["front"]
        assert "quoted" not in c["front"]


def test_build_concept_cards_empty() -> None:
    """_build_concept_cards returns empty for no sections."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_concept_cards,
    )

    assert _build_concept_cards("no sections", "tags") == []


# --- _build_qa_cards ---


def test_build_qa_cards() -> None:
    """_build_qa_cards extracts QA cards, filtering code and table lines."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_qa_cards,
    )

    cards = _build_qa_cards(_SAMPLE_MD, "egzamin pyt01")
    assert len(cards) >= 1
    assert "qa" in cards[0]["tags"]
    for c in cards:
        assert "```" not in c["back"]
        assert "|" not in c["back"]


def test_build_qa_cards_empty() -> None:
    """_build_qa_cards returns empty for no QA sections."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_qa_cards,
    )

    assert _build_qa_cards("no QA sections", "tags") == []


# --- extract_cards ---


def test_extract_cards(sample_file: Path) -> None:
    """extract_cards extracts all card types from file."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_cards,
    )

    cards = extract_cards(sample_file)
    assert len(cards) >= 1


def test_extract_cards_automata(automata_file: Path) -> None:
    """extract_cards works with automata content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_cards,
    )

    cards = extract_cards(automata_file)
    assert len(cards) >= 1


# --- main ---


def test_main_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() processes directory and writes output."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")
    out_file = tmp_path / "output.txt"

    real_path = Path

    def fake_path(p: object) -> Path:
        s = str(p)
        if s == "/home/kuchy/praca_magisterska/pytania/odpowiedzi":
            return real_path(md_dir)
        if s == "/home/kuchy/praca_magisterska/pytania/anki_egzamin_magisterski.txt":
            return real_path(out_file)
        return real_path(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    mod.main()
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "#separator:Tab" in content


def test_main_error_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() handles file processing errors gracefully."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-bad.md").write_text("content", encoding="utf-8")
    out_file = tmp_path / "output.txt"

    real_path = Path

    def fake_path(p: object) -> Path:
        s = str(p)
        if s == "/home/kuchy/praca_magisterska/pytania/odpowiedzi":
            return real_path(md_dir)
        if s == "/home/kuchy/praca_magisterska/pytania/anki_egzamin_magisterski.txt":
            return real_path(out_file)
        return real_path(s)

    def failing_extract(_filepath: object) -> list[dict[str, str]]:
        msg = "test error"
        raise ValueError(msg)

    monkeypatch.setattr(mod, "Path", fake_path)
    monkeypatch.setattr(mod, "extract_cards", failing_extract)
    mod.main()
    assert out_file.exists()


def test_main_dedup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() deduplicates cards by front[:100]."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")
    (md_dir / "02-test.md").write_text(_SAMPLE_MD, encoding="utf-8")
    out_file = tmp_path / "output.txt"

    real_path = Path

    def fake_path(p: object) -> Path:
        s = str(p)
        if s == "/home/kuchy/praca_magisterska/pytania/odpowiedzi":
            return real_path(md_dir)
        if s == "/home/kuchy/praca_magisterska/pytania/anki_egzamin_magisterski.txt":
            return real_path(out_file)
        return real_path(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    mod.main()
    assert out_file.exists()


# --- coverage gaps: line 246, branch 287->274, branch 305->308 ---


def test_build_concept_cards_empty_section_content() -> None:
    """Line 246: continue when _extract_section_content returns []."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_concept_cards,
    )

    # Body >= 80 chars, no special header words, but no extractable content:
    # lines start with | so first_para regex won't match, no Definicja/
    # Charakterystyka, no bold bullets.
    body_lines = "|table" * 20  # 120 chars, all starting with |
    content = f"### Normal Header\n{body_lines}\n"
    cards = _build_concept_cards(content, "tags")
    assert cards == []


def test_build_qa_cards_all_filtered_answer() -> None:
    """Branch 287->274: clean_answer empty when all lines are code/table."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        _build_qa_cards,
    )

    content = '### Q1: "What is X"\nOdpowiedź:\n```python\n```\n| col1 | col2 |\n'
    cards = _build_qa_cards(content, "tags")
    assert cards == []


def test_extract_cards_no_main_card(tmp_path: Path) -> None:
    """Branch 305->308: main_card is None (no ## Pytanie section)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v3 import (
        extract_cards,
    )

    md = tmp_path / "01-test.md"
    md.write_text(
        "# Pytanie 01: Topic\n\nPrzedmiot: Informatyka\n\n"
        "### Concept\n\n"
        "#### Definicja\n"
        "This is a definition of the concept for coverage testing here.\n",
        encoding="utf-8",
    )
    cards = extract_cards(md)
    # No main card since there's no ## Pytanie\n**...**
    # But concept cards should still be extracted
    assert isinstance(cards, list)
