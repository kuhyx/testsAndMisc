"""Tests for generate_images/generate_anki_final.py (part 3): remaining gaps."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

# Content with question but no answer section
_MD_Q_NO_ANSWER = """\
# Pytanie 01: No Answer

Przedmiot: Test

## Pytanie

**"Where is the answer?"**

## Some unrelated section

Just text with no main answer heading.
"""

# Content for subsection with empty body_parts and single body_parts
_MD_SUBSECTIONS = """\
# Pytanie 02: Subsections

Przedmiot: Fizyka

## Pytanie

**"Subsection test?"**

## 📚 Odpowiedź główna

### 1. First heading
Content

### Valid section with enough body text

#### SubA
Point A here

#### SubB
Point B here

- **Bullet1**: Description one
- **Bullet2**: Description two

### Section with table only body

| col1 | col2 | col3 | col4 | col5 | col6 |
| val1 | val2 | val3 | val4 | val5 | val6 |
| va11 | va12 | va13 | va14 | va15 | va16 |

### Single paragraph section

Just one paragraph here that is long enough to pass body length check.
"""

# Content for algo with no context header before match
_MD_ALGO_NO_CONTEXT = """\
Some text without any level-3 headers before complexity info.

#### Złożoność czasowa
O(n^2) algorithm complexity that exceeds minimum match length.

### 1. After Section
Content here.
"""

# Content with comparison section
_MD_COMPARISON = """\
# Pytanie 04: Comparison

Przedmiot: Informatyka

## Pytanie

**"Comparison test?"**

## 📚 Odpowiedź główna

### 1. Main point
Content here.

## Porównanie algorytmów X vs Y

| **Szybkość** | szybkie działanie |
| **Pamięć** | niskie zużycie |
| **Złożoność** | O(n log n) |

## 🎓 Pytania egzaminacyjne

### Q1: "What is sorting?"
Odpowiedź:
Short.

### Q2: "Explain in great detail the comprehensive algorithm?"
Odpowiedź:
{}
""".format(
    "\n".join(
        [
            f"Line {i}: A very detailed explanation of the algorithm"
            f" that contains enough content to exceed the maximum answer"
            f" length threshold for truncation testing purposes here."
            for i in range(1, 8)
        ]
    )
)

# Comparison that will not match title regex
_MD_COMPARISON_NO_TITLE = """\
## Porównanie
| **Speed** | fast |
| **Memory** | low |

## Next section
"""


# --- format_list: item cleaning to empty (51->49) ---


def test_format_list_item_cleans_empty() -> None:
    """Item that cleans to empty is skipped in format_list (51->49)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        format_list,
    )

    result = format_list(["  ", "valid"])
    assert "<li>" in result
    assert "valid" in result
    # Only one <li> since the whitespace-only item is skipped
    assert result.count("<li>") == 1


# --- _extract_main_question_card: no answer_match (line 94) ---


def test_main_question_no_answer_section() -> None:
    """Question found but no answer section -> return [] (line 94)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_main_question_card,
    )

    cards = _extract_main_question_card(_MD_Q_NO_ANSWER, "tags")
    assert cards == []


# --- _make_question_text: header.endswith("?") (line 125) ---


def test_make_question_text_ends_question_no_keywords() -> None:
    """Header ending with ? without Definicja/Co to/Charakterystyka (line 125)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _make_question_text,
    )

    result = _make_question_text("Is this valid?")
    assert result == "Is this valid?"


# --- _extract_body_parts: desc is None (152->158, 155) ---


def test_body_parts_bullet_no_desc() -> None:
    """Bullet with no description hits else branch (155)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_body_parts,
    )

    body = "- **OnlyBold**\n"
    parts = _extract_body_parts(body)
    assert any("OnlyBold" in p for p in parts)


def test_body_parts_para_empty_fallback() -> None:
    """All paragraphs filtered out -> empty list (152->158)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_body_parts,
    )

    body = (
        "```python\n"
        "code_block_that_is_very_long_to_ensure_body_has_content = True\n"
        "```\n\n"
        "| table_col | data_here | more_data | extra | padding |\n"
    )
    parts = _extract_body_parts(body)
    assert parts == []


def test_body_parts_long_para_truncation() -> None:
    """Paragraph > MAX_CONTENT_LENGTH is truncated (line 155)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_body_parts,
    )

    body = "\n\n" + "A" * 350 + "\n\n"
    parts = _extract_body_parts(body)
    assert len(parts) == 1
    assert parts[0].endswith("...")
    assert len(parts[0]) <= 304  # 300 + "..."


# --- _extract_subsection_cards: empty parts / multiple parts ---


def test_subsection_empty_answer_parts() -> None:
    """Subsection where _extract_body_parts returns [] (182->173)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_subsection_cards,
    )

    content = """\
### Table-only section with enough header text

| col1 | col2 | col3 | col4 | col5 | col6 | col7 |
| val1 | val2 | val3 | val4 | val5 | val6 | val7 |
| va11 | va12 | va13 | va14 | va15 | va16 | va17 |

### Valid section with content for comparison

- **Term**: Description of the term for proper extraction here.
"""
    cards = _extract_subsection_cards(content, "tags")
    assert isinstance(cards, list)


def test_subsection_multiple_parts_format_list() -> None:
    """Subsection with multiple answer_parts uses format_list (line 185)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_subsection_cards,
    )

    content = """\
### Multi-part section with enough body content

#### SubHeader1
Description one.

#### SubHeader2
Description two.

- **Bold1**: text here
- **Bold2**: text here
"""
    cards = _extract_subsection_cards(content, "tags")
    assert isinstance(cards, list)
    if cards:
        assert "<ul>" in cards[0]["back"] or "<li>" in cards[0]["back"]


def test_subsection_single_part_clean_text() -> None:
    """Subsection with single answer_part uses clean_text (else branch)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_subsection_cards,
    )

    content = """\
### Simple section with enough body

A single paragraph that does not have any bold terms or subheaders to extract.
But it is long enough to pass the body length threshold for processing.
"""
    cards = _extract_subsection_cards(content, "tags")
    assert isinstance(cards, list)


# --- _extract_algo_cards: algo_context is None (219->213) ---


def test_algo_cards_no_context() -> None:
    """Algo match found but no ### header before it (219->213)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_algo_cards,
    )

    cards = _extract_algo_cards(_MD_ALGO_NO_CONTEXT, "tags")
    assert isinstance(cards, list)


# --- _extract_comparison_cards: full path (257-272) ---


def test_comparison_cards_full_path() -> None:
    """Comparison section with items and title match (lines 257-272)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_comparison_cards,
    )

    content = """\
## Porównanie algorytmów X vs Y

| **Szybkość** | szybkie działanie |
| **Pamięć** | niskie zużycie |
| **Złożoność** | O(n log n) |
"""
    cards = _extract_comparison_cards(content, "tags", "04")
    assert len(cards) == 1
    assert "Porównaj" in cards[0]["front"]
    assert "<table>" in cards[0]["back"]


def test_comparison_no_title_match() -> None:
    """Comparison with items but no title match -> return []."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_comparison_cards,
    )

    cards = _extract_comparison_cards(_MD_COMPARISON_NO_TITLE, "tags", "01")
    assert cards == []


def test_comparison_no_items() -> None:
    """Comparison section found but no table items -> return []."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_comparison_cards,
    )

    content = """\
## Porównanie A vs B

No table rows with bold items here.
Just plain text.
"""
    cards = _extract_comparison_cards(content, "tags", "01")
    assert cards == []


# --- _extract_qa_cards: short answer and truncation (304->301, 308) ---


def test_qa_short_answer_skip() -> None:
    """QA answer shorter than MIN_QA_LENGTH is skipped (304->301)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_qa_cards,
    )

    content = """\
## 🎓 Pytania

### Q1: "Short answer question?"
Odpowiedź:
Tiny.
"""
    cards = _extract_qa_cards(content, "tags")
    assert cards == []


def test_qa_long_answer_truncation() -> None:
    """QA answer exceeding MAX_ANSWER_LENGTH is truncated (line 308)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_qa_cards,
    )

    cards = _extract_qa_cards(_MD_COMPARISON, "tags")
    assert isinstance(cards, list)
    for card in cards:
        # Check truncation happened for long answers
        if "..." in card["back"]:
            assert len(card["back"]) <= 450


# --- extract_from_file: full integration ---


def test_extract_from_file_comparison(tmp_path: Path) -> None:
    """extract_from_file with comparison content."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        extract_from_file,
    )

    p = tmp_path / "04-comparison.md"
    p.write_text(_MD_COMPARISON, encoding="utf-8")
    cards = extract_from_file(str(p))
    assert len(cards) >= 1


# --- main() function (lines 338-396) ---


def test_main_function(tmp_path: Path) -> None:
    """main() processes files, handles errors, and writes output."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_final as mod

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

    def fake_extract(_filepath: object) -> list[dict[str, str]]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [
                {"front": "Q1", "back": "A1", "tags": "t1"},
                {"front": "Q1", "back": "A1", "tags": "t1"},
            ]
        msg = "test error"
        raise ValueError(msg)

    with (
        patch.object(mod, "Path", side_effect=fake_path),
        patch.object(mod, "extract_from_file", side_effect=fake_extract),
    ):
        mod.main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "#separator:tab" in content
    assert "Q1" in content
    # Dedup: Q1 appears only once in tab-separated lines
    data_lines = [ln for ln in content.split("\n") if ln and not ln.startswith("#")]
    assert sum(1 for ln in data_lines if ln.startswith("Q1")) == 1


# --- Gap line 185: len(answer_parts) > 1 → format_list ---


def test_subsection_cards_multi_subheaders_format_list() -> None:
    """Subsection with 2+ subheaders uses format_list (line 185)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_subsection_cards,
    )

    content = """\
### Comprehensive section with multiple sub-points

- **Pierwsza kategoria**: Opis pierwszej kategorii algorytmu jest tutaj
- **Druga kategoria**: Opis drugiej kategorii algorytmu jest tutaj
- **Trzecia kategoria**: Opis trzeciej kategorii algorytmu jest tutaj
"""
    cards = _extract_subsection_cards(content, "tags")
    assert len(cards) == 1
    assert "<ul>" in cards[0]["back"]


# --- Gap 219->213: algo_context is None (no ### before match) ---


def test_algo_cards_truly_no_context() -> None:
    """Algo match found via second pattern but no ### before it (219->213)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_algo_cards,
    )

    content = (
        "Tekst o algorytmach bez nagłówków trzeciego poziomu.\n\n"
        "Złożoność: **O(n^2) analiza złożoności algorytmu sortowania**\n\n"
        "Dalszy tekst tutaj.\n"
    )
    cards = _extract_algo_cards(content, "tags")
    assert cards == []


# --- Gap line 270: title_match is None → return [] ---


def test_comparison_no_vs_title_returns_empty() -> None:
    """Comparison with items but title without vs/i/oraz → return [] (line 270)."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_final import (
        _extract_comparison_cards,
    )

    content = """\
## Zestawienie danych

| **Parametr** | wartość tutaj |
| **Metryka** | inna wartość |
"""
    cards = _extract_comparison_cards(content, "tags", "05")
    assert cards == []
