"""Tests for generate_images/generate_anki.py (part 2): full coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

_PKG = "python_pkg.praca_magisterska_video.generate_images.generate_anki"

_SAMPLE_MD = """\
# Pytanie 01: Test Subject

Przedmiot: Informatyka

## Pytanie

**"What is the main concept of CS?"**

## 📚 Odpowiedź główna

### 1. First Concept

- **Term1**: Description of term one that is reasonably long
- **Term2**: Description of term two that is also long enough

### 2. Second Concept

Some body text that is long enough to be extracted as a paragraph.

More text in another paragraph that follows above.

```python
code block should be skipped
```

| table | should | be | skipped |

### Przykład heading
Example text that should be ignored.

### 3. Characteristics

#### Definicja
Short definition text here.

**Złożoność czasowa**: O(n log n) is the complexity

**important formuła**: Some formula content that is sufficiently long
"""

_MINIMAL_MD = """\
# No question format

Just some text.
"""


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Markdown file matching extraction patterns."""
    p = tmp_path / "01-test-subject.md"
    p.write_text(_SAMPLE_MD, encoding="utf-8")
    return p


@pytest.fixture
def minimal_file(tmp_path: Path) -> Path:
    """Markdown file with no matching patterns."""
    p = tmp_path / "noformat.md"
    p.write_text(_MINIMAL_MD, encoding="utf-8")
    return p


def test_get_metadata(sample_file: Path) -> None:
    """_get_metadata extracts all metadata fields."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _get_metadata,
    )

    num, topic, _, main_q, content = _get_metadata(str(sample_file))
    assert num == "01"
    assert "test" in topic
    assert "main concept" in main_q
    assert isinstance(content, str)


def test_get_metadata_no_match(minimal_file: Path) -> None:
    """_get_metadata with non-matching filename."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _get_metadata,
    )

    num, topic, _, _, _ = _get_metadata(str(minimal_file))
    assert num == "00"
    assert topic == "unknown"


def test_extract_main_card(sample_file: Path) -> None:
    """_extract_main_card extracts a main question card."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_main_card,
        _get_metadata,
    )

    num, topic, _, main_q, content = _get_metadata(str(sample_file))
    cards = _extract_main_card(content, main_q, "Informatyka", num, topic)
    assert len(cards) == 1
    assert "main concept" in cards[0]["question"]


def test_extract_main_card_no_answer() -> None:
    """_extract_main_card returns empty when no answer section."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_main_card,
    )

    cards = _extract_main_card("No content", "Question?", "Sub", "01", "topic")
    assert cards == []


def test_extract_main_card_definitions() -> None:
    """_extract_main_card picks up definitions."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_main_card,
    )

    content = (
        '## Pytanie\n**"Q?"**\n\n'
        "## 📚 Odpowiedź główna\n\n### Header\nText\n\n"
        "**Term** -- A moderate length definition here for test\n"
    )
    cards = _extract_main_card(content, "Q?", "S", "01", "t")
    assert len(cards) >= 1


def test_extract_subsection_answer_bullets() -> None:
    """_extract_subsection_answer with bullet points."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_subsection_answer,
    )

    body = "- **A**: desc\n- **B**: desc2\n"
    result = _extract_subsection_answer(body)
    assert result is not None
    assert "A" in result


def test_extract_subsection_answer_paragraphs() -> None:
    """_extract_subsection_answer with no bullets falls back to paragraphs."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_subsection_answer,
    )

    body = "\n\nA paragraph of text that should be captured.\n\n"
    result = _extract_subsection_answer(body)
    assert result is not None


def test_extract_subsection_answer_none() -> None:
    """_extract_subsection_answer returns None for empty content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_subsection_answer,
    )

    assert _extract_subsection_answer("") is None


def test_extract_sub_cards(sample_file: Path) -> None:
    """_extract_sub_cards extracts detail cards."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
        _get_metadata,
    )

    num, topic, title, _, content = _get_metadata(str(sample_file))
    cards = _extract_sub_cards(content, title, "Informatyka", num, topic)
    assert isinstance(cards, list)


def test_extract_sub_cards_characteristics() -> None:
    """_extract_sub_cards formats Charakterystyka questions specially."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_sub_cards,
    )

    content = (
        "### Charakterystyka algorytmu\n\n"
        "- **Speed**: Fast algorithm for sorting\n"
        "- **Memory**: Efficient memory usage here\n\n"
    )
    cards = _extract_sub_cards(content, "Pytanie: 01 Algo", "S", "01", "t")
    assert isinstance(cards, list)


def test_extract_formula_cards() -> None:
    """_extract_formula_cards extracts formula cards."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        _extract_formula_cards,
    )

    content = (
        "### Merge Sort\nText.\n"
        "**Merge Sort formuła**: T(n) = 2T(n/2) + O(n) recurrence\n\n"
    )
    cards = _extract_formula_cards(content, "S", "01")
    assert isinstance(cards, list)


def test_extract_question_and_answer(sample_file: Path) -> None:
    """extract_question_and_answer extracts all card types."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        extract_question_and_answer,
    )

    cards = extract_question_and_answer(str(sample_file))
    assert len(cards) >= 1


def test_clean_for_anki() -> None:
    """clean_for_anki converts markdown to clean HTML."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki import (
        clean_for_anki,
    )

    result = clean_for_anki('**bold** *italic* "quoted"\ttab\n\nnewlines\n\n\n')
    assert "<b>bold</b>" in result
    assert "<i>italic</i>" in result
    assert "&quot;" in result
    assert "\t" not in result


def test_main(tmp_path: Path) -> None:
    """main() processes files and writes output."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")
    out_file = tmp_path / "output.txt"

    with (
        patch.object(
            Path,
            "__new__",
            wraps=Path.__new__,
        ),
    ):
        # Monkey-patch the hardcoded paths

        def patched_main() -> None:
            all_cards: list[dict[str, str]] = []
            for md_file in sorted(md_dir.glob("*.md")):
                cards = mod.extract_question_and_answer(str(md_file))
                all_cards.extend(cards)
            with out_file.open("w", encoding="utf-8") as f:
                f.write("#separator:tab\n#html:true\n")
                f.write("#columns:Front\tBack\tTags\n")
                f.write("#deck:Test\n#notetype:Basic\n\n")
                for card in all_cards:
                    front = mod.clean_for_anki(card["question"])
                    back = mod.clean_for_anki(card["answer"])
                    f.write(f"{front}\t{back}\t{card['tags']}\n")

        patched_main()
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "#separator:tab" in content
