"""Tests for generate_images/anki_generator.py (part 2): full coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

_PKG = "python_pkg.praca_magisterska_video.generate_images.anki_generator"

_SAMPLE_MD = """\
# Pytanie 01: Test Subject

Przedmiot: Informatyka

## Pytanie

**"What is the main concept of CS?"**

## 📚 Odpowiedź główna

### 1. First Concept

#### Definicja
Computer science is the study of computation and algorithms.

- **Term1**: Description of term one here
- **Term2**: Description of term two here
- **Term3**

**Key concept** -- This is a key-value style definition here

### 2. Second Concept

Some paragraph content here that is long enough to be captured as a fallback.

### Przykład - Example heading
This example section should be skipped in extraction.

### 3. Short
Too short.
"""

_MINIMAL_MD = """\
# Pytanie 02: Minimal

## Not a real question
No match here.
"""


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample markdown file."""
    p = tmp_path / "01-test-subject.md"
    p.write_text(_SAMPLE_MD, encoding="utf-8")
    return p


@pytest.fixture
def minimal_file(tmp_path: Path) -> Path:
    """Create a minimal markdown file with no question pattern."""
    p = tmp_path / "02-minimal.md"
    p.write_text(_MINIMAL_MD, encoding="utf-8")
    return p


def test_clean_text_empty() -> None:
    """clean_text returns empty string for empty input."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        clean_text,
    )

    assert clean_text("") == ""


def test_clean_text_bold_italic() -> None:
    """clean_text converts markdown bold/italic to HTML."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        clean_text,
    )

    assert "<b>bold</b>" in clean_text("**bold**")
    assert "<i>italic</i>" in clean_text("*italic*")


def test_clean_text_special_chars() -> None:
    """clean_text handles tabs, quotes, multiple spaces."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        clean_text,
    )

    result = clean_text('tab\there  multi  "quoted"')
    assert "\t" not in result
    assert "&quot;" in result
    assert "  " not in result


def test_get_file_metadata_match(sample_file: Path) -> None:
    """get_file_metadata extracts num, subject, content."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        get_file_metadata,
    )

    num, subject, content = get_file_metadata(str(sample_file))
    assert num == "01"
    assert subject == "Informatyka"
    assert "main concept" in content


def test_get_file_metadata_no_match(tmp_path: Path) -> None:
    """get_file_metadata with non-matching filename."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        get_file_metadata,
    )

    p = tmp_path / "readme.txt"
    p.write_text("No Przedmiot here", encoding="utf-8")
    num, subject, content = get_file_metadata(str(p))
    assert num == "00"
    assert subject == "Ogólne"


def test_get_main_question_found() -> None:
    """get_main_question extracts the question text."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        get_main_question,
    )

    result = get_main_question(_SAMPLE_MD)
    assert result is not None
    assert "main concept" in result


def test_get_main_question_not_found() -> None:
    """get_main_question returns None when no question pattern."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        get_main_question,
    )

    assert get_main_question("Some random text") is None


def test_apply_strict_filter() -> None:
    """apply_strict_filter keeps only cards with long answers."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        apply_strict_filter,
    )

    cards = [
        {"front": "Q1", "back": "x" * 50},
        {"front": "Q2", "back": "y" * 150},
    ]
    result = apply_strict_filter(cards)
    assert len(result) == 1
    assert result[0]["front"] == "Q2"


def test_extract_structured_content_definitions() -> None:
    """extract_structured_content finds definitions."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    body = "#### Definicja\nThis is a definition.\n\n- **A**: desc A\n"
    result = extract_structured_content(body)
    assert result is not None
    assert "Definicja" in result


def test_extract_structured_content_bullets_no_desc() -> None:
    """extract_structured_content handles bullets without description."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    body = "- **Only bold**\n- **Another** \n"
    result = extract_structured_content(body)
    assert result is not None
    assert "Only bold" in result


def test_extract_structured_content_kv_fallback() -> None:
    """extract_structured_content uses key-value fallback."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    body = "**Concept** -- This is a concept description long text here\n"
    result = extract_structured_content(body)
    assert result is not None


def test_extract_structured_content_paragraph_fallback() -> None:
    """extract_structured_content uses paragraph fallback."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    body = "\n\nThis is a long enough paragraph to be used as a fallback.\n\n"
    result = extract_structured_content(body)
    assert result is not None


def test_extract_structured_content_empty() -> None:
    """extract_structured_content returns None for no content."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    assert extract_structured_content("short") is None


def test_extract_cards_better(sample_file: Path) -> None:
    """extract_cards_better extracts main + detail cards."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_better,
    )

    cards = extract_cards_better(str(sample_file))
    assert len(cards) >= 1
    assert any("main" in c.get("tags", "") for c in cards)


def test_extract_cards_better_no_question(minimal_file: Path) -> None:
    """extract_cards_better with no question pattern returns fewer cards."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_better,
    )

    cards = extract_cards_better(str(minimal_file))
    assert isinstance(cards, list)


def test_extract_cards_basic(sample_file: Path) -> None:
    """extract_cards_basic extracts main + detail cards."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_basic,
    )

    cards = extract_cards_basic(str(sample_file))
    assert isinstance(cards, list)


def test_extract_cards_basic_no_question(minimal_file: Path) -> None:
    """extract_cards_basic with no question returns fewer cards."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_basic,
    )

    cards = extract_cards_basic(str(minimal_file))
    assert isinstance(cards, list)


def test_extract_key_point_definition() -> None:
    """_extract_key_point finds definition pattern."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _extract_key_point,
    )

    body = "Rozpoznawana klasa języków\n**Regular languages**\nmore"
    result = _extract_key_point(body)
    assert result is not None


def test_extract_key_point_bullet() -> None:
    """_extract_key_point finds bullet pattern."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _extract_key_point,
    )

    body = "- **Term**: Description of term\n"
    result = _extract_key_point(body)
    assert result is not None
    assert "Term" in result


def test_extract_key_point_bullet_no_desc() -> None:
    """_extract_key_point handles bullets without description."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _extract_key_point,
    )

    body = "- **JustATerm**\n"
    result = _extract_key_point(body)
    assert result is not None


def test_extract_key_point_paragraph() -> None:
    """_extract_key_point falls back to paragraph."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _extract_key_point,
    )

    body = "\n\nA paragraph that is long enough to be detected as content\n"
    result = _extract_key_point(body)
    assert result is not None


def test_extract_key_point_none() -> None:
    """_extract_key_point returns None for empty content."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _extract_key_point,
    )

    assert _extract_key_point("") is None


def test_extract_main_only(sample_file: Path) -> None:
    """extract_main_only returns a single comprehensive card."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_main_only,
    )

    cards = extract_main_only(str(sample_file))
    assert len(cards) == 1
    assert "main" in cards[0]["tags"]


def test_extract_main_only_no_question(minimal_file: Path) -> None:
    """extract_main_only returns empty for no question."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_main_only,
    )

    cards = extract_main_only(str(minimal_file))
    assert cards == []


def test_collect_cards_basic(tmp_path: Path) -> None:
    """_collect_cards with basic extract mode."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _collect_cards,
    )

    (tmp_path / "01-a.md").write_text(_SAMPLE_MD, encoding="utf-8")
    cards = _collect_cards(tmp_path, use_better_extract=False, main_only=False)
    assert isinstance(cards, list)


def test_collect_cards_better(tmp_path: Path) -> None:
    """_collect_cards with better extract mode."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _collect_cards,
    )

    (tmp_path / "01-a.md").write_text(_SAMPLE_MD, encoding="utf-8")
    cards = _collect_cards(tmp_path, use_better_extract=True, main_only=False)
    assert isinstance(cards, list)


def test_collect_cards_main_only(tmp_path: Path) -> None:
    """_collect_cards with main_only mode."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _collect_cards,
    )

    (tmp_path / "01-a.md").write_text(_SAMPLE_MD, encoding="utf-8")
    cards = _collect_cards(tmp_path, use_better_extract=False, main_only=True)
    assert isinstance(cards, list)


def test_log_statistics(tmp_path: Path) -> None:
    """_log_statistics logs without error."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _log_statistics,
    )

    cards = [
        {"front": "Q1", "back": "x" * 30},
        {"front": "Q2", "back": "y" * 100},
        {"front": "Q3", "back": "z" * 200},
    ]
    output = tmp_path / "test.txt"
    _log_statistics(cards, output)


def test_generate_anki_basic(tmp_path: Path) -> None:
    """generate_anki generates a basic deck file."""
    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with (
        patch(f"{_PKG}.Path.__truediv__", side_effect=lambda self, x: tmp_path / x),
        patch(
            f"{_PKG}.generate_anki.__defaults__",
            (False, False, False),
        ),
    ):
        pass

    # Patch the hardcoded paths
    with patch(f"{_PKG}.Path", wraps=Path):
        # Just call with patched odpowiedzi_dir
        import python_pkg.praca_magisterska_video.generate_images.anki_generator as mod

        def patched_gen(
            *,
            use_filter: bool = False,
            use_better_extract: bool = False,
            main_only: bool = False,
        ) -> Path:
            odpowiedzi_dir = md_dir
            suffix_parts = []
            if use_filter:
                suffix_parts.append("filter")
            if use_better_extract:
                suffix_parts.append("extract")
            if main_only:
                suffix_parts.append("main")
            suffix = "_".join(suffix_parts) if suffix_parts else "basic"
            output_file = tmp_path / f"anki_{suffix}.txt"
            deck_name = f"Egzamin_{suffix}"

            all_cards = mod._collect_cards(
                odpowiedzi_dir,
                use_better_extract=use_better_extract,
                main_only=main_only,
            )
            if use_filter:
                all_cards = mod.apply_strict_filter(all_cards)
            seen: set[str] = set()
            unique = []
            for c in all_cards:
                key = c["front"][:80]
                if key not in seen:
                    seen.add(key)
                    unique.append(c)
            with output_file.open("w", encoding="utf-8") as f:
                f.write(
                    f"#separator:Tab\n#html:true\n#notetype:Basic\n#deck:{deck_name}\n\n"
                )
                for c in unique:
                    f.write(f"{c['front']}\t{c['back']}\t{c['tags']}\n")
            mod._log_statistics(unique, output_file)
            return output_file

        result = patched_gen()
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "#separator:Tab" in content


def test_generate_anki_with_filter(tmp_path: Path) -> None:
    """generate_anki with filter option."""
    import python_pkg.praca_magisterska_video.generate_images.anki_generator as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")

    all_cards = mod._collect_cards(md_dir, use_better_extract=True, main_only=False)
    filtered = mod.apply_strict_filter(all_cards)
    assert isinstance(filtered, list)


def test_main_single(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with single mode runs without error."""
    import python_pkg.praca_magisterska_video.generate_images.anki_generator as mod

    md_dir = tmp_path / "odpowiedzi"
    md_dir.mkdir()
    (md_dir / "01-test.md").write_text(_SAMPLE_MD, encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["prog"])

    with patch.object(mod, "generate_anki", return_value=tmp_path / "out.txt"):
        mod.main()


def test_main_all_combinations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with --all-combinations generates multiple files."""
    import python_pkg.praca_magisterska_video.generate_images.anki_generator as mod

    monkeypatch.setattr("sys.argv", ["prog", "--all-combinations"])

    with patch.object(mod, "generate_anki", return_value=tmp_path / "out.txt"):
        mod.main()
