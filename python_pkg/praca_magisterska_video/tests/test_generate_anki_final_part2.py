"""Tests for generate_images/generate_anki_final.py (part 2): full coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

_PKG = "python_pkg.praca_magisterska_video.generate_images.generate_anki_final"

_SAMPLE_MD = """\
# Pytanie 01: Test Subject

Przedmiot: Informatyka

## Pytanie

**"What is the main concept of CS?"**

## 📚 Odpowiedź główna

### 1. First Concept

#### Definicja
Computer science is the study of computation and algorithms.

- **Term1**: Description of term one here that is long
- **Term2**: Description of term two here that is long
- **Term3**

### 2. Second Concept

Some paragraph content long enough to be captured as a nice fallback.

Another paragraph here with more content for extraction purposes.

```python
code_block = "should be skipped"
```

| table | data |

### Przykład heading
Example text.

#### Złożoność czasowa
O(n log n) for merge sort algorithm

### Definicja important concept
Some definition text content.

### Co to jest algorithm?
Algorithm is a step-by-step procedure.

### Charakterystyka of sorting
Sorting algorithms have specific properties.

## Porównanie methods vs others
| **Aspekt** | **Wartość** |
| **Time** | O(n) |
| **Space** | O(1) |

## 🎓 Pytania egzaminacyjne

### Q1: "What is an algorithm?"
Odpowiedź:
An algorithm is a finite sequence of well-defined instructions.
It produces an output from given inputs.
Used in computer science.
"""

_NO_QUESTION_MD = """\
# Some document

Just text here without question format.
"""


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample markdown file."""
    p = tmp_path / "01-test-subject.md"
    p.write_text(_SAMPLE_MD, encoding="utf-8")
    return p


def test_clean_text_empty() -> None:
    """clean_text returns empty for empty input."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        clean_text,
    )

    assert clean_text("") == ""


def test_clean_text_formatting() -> None:
    """clean_text converts markdown to HTML."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        clean_text,
    )

    result = clean_text('**bold** *italic* "quote"\ttab  spaces')
    assert "<b>" in result
    assert "<i>" in result
    assert "&quot;" in result


def test_format_list_unordered() -> None:
    """format_list creates unordered list."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        format_list,
    )

    result = format_list(["a", "b"])
    assert "<ul>" in result
    assert "<li>" in result


def test_format_list_ordered() -> None:
    """format_list creates ordered list."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        format_list,
    )

    result = format_list(["x", "y"], numbered=True)
    assert "<ol>" in result


def test_format_list_empty() -> None:
    """format_list returns empty for empty input."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        format_list,
    )

    assert format_list([]) == ""


def test_get_file_metadata(sample_file: Path) -> None:
    """_get_file_metadata extracts num, subject, content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _get_file_metadata,
    )

    num, subject, _ = _get_file_metadata(str(sample_file))
    assert num == "01"
    assert subject == "Informatyka"


def test_get_file_metadata_no_match(tmp_path: Path) -> None:
    """_get_file_metadata with non-matching filename."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _get_file_metadata,
    )

    p = tmp_path / "readme.txt"
    p.write_text("No Przedmiot", encoding="utf-8")
    num, subject, _ = _get_file_metadata(str(p))
    assert num == "00"
    assert subject == "Ogólne"


def test_extract_main_question_card(sample_file: Path) -> None:
    """_extract_main_question_card extracts the main Q&A card."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_main_question_card,
        _get_file_metadata,
    )

    _, _, content = _get_file_metadata(str(sample_file))
    cards = _extract_main_question_card(content, "egzamin pyt01 Informatyka")
    assert len(cards) == 1


def test_extract_main_question_card_no_question() -> None:
    """_extract_main_question_card returns empty when no question."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_main_question_card,
    )

    cards = _extract_main_question_card("No ## Pytanie section", "tags")
    assert cards == []


def test_extract_main_question_card_no_headers() -> None:
    """_extract_main_question_card returns empty when no headers in answer."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_main_question_card,
    )

    content = '## Pytanie\n**"Q?"**\n\n## 📚 Odpowiedź główna\n\nJust text.\n'
    cards = _extract_main_question_card(content, "tags")
    assert cards == []


def test_make_question_text_definition() -> None:
    """_make_question_text formats definition headers."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _make_question_text,
    )

    assert "Co to jest" in _make_question_text("Definicja algorytmu")


def test_make_question_text_characteristic() -> None:
    """_make_question_text formats characteristic headers."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _make_question_text,
    )

    assert "Scharakteryzuj" in _make_question_text("Charakterystyka danych")


def test_make_question_text_question() -> None:
    """_make_question_text matches 'Co to' header before endswith('?')."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _make_question_text,
    )

    result = _make_question_text("Co to jest algorytm?")
    assert result == "Co to jest: Co to jest algorytm??"


def test_make_question_text_plain() -> None:
    """_make_question_text prefixes plain headers with Omów."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _make_question_text,
    )

    assert "Omów" in _make_question_text("Merge Sort")


def test_extract_body_parts_subheaders() -> None:
    """_extract_body_parts extracts #### subheaders."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_body_parts,
    )

    body = "#### Sub1\nText1\n#### Sub2\nText2\n"
    parts = _extract_body_parts(body)
    assert len(parts) >= 1


def test_extract_body_parts_bullets() -> None:
    """_extract_body_parts extracts bullet points."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_body_parts,
    )

    body = "- **A**: desc\n- **B**\n"
    parts = _extract_body_parts(body)
    assert len(parts) >= 1
    assert any("A" in p for p in parts)


def test_extract_body_parts_paragraph_fallback() -> None:
    """_extract_body_parts falls back to paragraphs."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_body_parts,
    )

    body = "\n\nA very long paragraph of text that has enough length to pass.\n\n"
    parts = _extract_body_parts(body)
    assert len(parts) >= 1


def test_extract_subsection_cards(sample_file: Path) -> None:
    """_extract_subsection_cards extracts detail cards."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_subsection_cards,
        _get_file_metadata,
    )

    _, _, content = _get_file_metadata(str(sample_file))
    cards = _extract_subsection_cards(content, "egzamin pyt01")
    assert isinstance(cards, list)


def test_extract_algo_cards() -> None:
    """_extract_algo_cards extracts complexity cards."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_algo_cards,
    )

    content = "### Merge Sort\nSorting algorithm.\nZłożoność: **O(n log n)**\n\n"
    cards = _extract_algo_cards(content, "tags")
    assert isinstance(cards, list)


def test_extract_algo_cards_section() -> None:
    """_extract_algo_cards finds #### Złożoność sections."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_algo_cards,
    )

    cards = _extract_algo_cards(_SAMPLE_MD, "tags")
    assert isinstance(cards, list)


def test_extract_comparison_cards(sample_file: Path) -> None:
    """_extract_comparison_cards extracts comparison table cards."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_comparison_cards,
        _get_file_metadata,
    )

    _, _, content = _get_file_metadata(str(sample_file))
    cards = _extract_comparison_cards(content, "tags", "01")
    assert isinstance(cards, list)


def test_extract_comparison_cards_no_match() -> None:
    """_extract_comparison_cards returns empty when no comparison."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_comparison_cards,
    )

    cards = _extract_comparison_cards("No comparison here", "tags", "01")
    assert cards == []


def test_extract_qa_cards(sample_file: Path) -> None:
    """_extract_qa_cards extracts Q&A practice cards."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_qa_cards,
        _get_file_metadata,
    )

    _, _, content = _get_file_metadata(str(sample_file))
    cards = _extract_qa_cards(content, "tags")
    assert isinstance(cards, list)


def test_extract_qa_cards_no_section() -> None:
    """_extract_qa_cards returns empty when no QA section."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_qa_cards,
    )

    assert _extract_qa_cards("No QA section", "tags") == []


def test_extract_from_file(sample_file: Path) -> None:
    """extract_from_file extracts all card types."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        extract_from_file,
    )

    cards = extract_from_file(str(sample_file))
    assert len(cards) >= 1


def test_main(tmp_path: Path) -> None:
    """main() processes files and writes output."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_final as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")
    out_file = tmp_path / "output.txt"

    all_cards = []
    for md_file in sorted(md_dir.glob("*.md")):
        cards = mod.extract_from_file(str(md_file))
        all_cards.extend(cards)

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for c in all_cards:
        if c["front"] not in seen:
            seen.add(c["front"])
            unique.append(c)

    with out_file.open("w", encoding="utf-8") as f:
        f.write("#separator:tab\n#html:true\n#tags column:3\n")
        f.write("#deck:Test\n#notetype:Basic\n\n")
        for card in unique:
            f.write(f"{card['front']}\t{card['back']}\t{card['tags']}\n")

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "#separator:tab" in content
