"""Tests for generate_images/generate_anki_v2.py (part 2): full coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

_SAMPLE_MD = """\
# Pytanie 01: Test Subject

Przedmiot: Informatyka

## Pytanie

**"What is the main concept of CS?"**

## 📚 Odpowiedź główna

### 1. First Concept Long Title

- **Term1**: Description of term one here
- **Term2**: Description of term two here

### 2. Second Concept

More text here.

**Definition** -- A 30-char-plus definition text here for extraction

**Przykład note** -- Should be excluded
**Uwaga note** -- Should also be excluded
"""

_MINIMAL_MD = """\
# Some title

Just text without subject or question format.
"""

_FALLBACK_MD = """\
# Pytanie 02: Fallback

## Pytanie

Not matching pattern.
"""


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Markdown file matching extraction patterns."""
    p = tmp_path / "01-test-subject.md"
    p.write_text(_SAMPLE_MD, encoding="utf-8")
    return p


@pytest.fixture
def minimal_file(tmp_path: Path) -> Path:
    """Markdown file with no patterns."""
    p = tmp_path / "readme.txt"
    p.write_text(_MINIMAL_MD, encoding="utf-8")
    return p


def test_extract_main_question_found() -> None:
    """extract_main_question finds the question."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_main_question,
    )

    result = extract_main_question(_SAMPLE_MD, "01-test.md")
    assert "main concept" in result


def test_extract_main_question_fallback_title() -> None:
    """extract_main_question falls back to title."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_main_question,
    )

    result = extract_main_question(_MINIMAL_MD, "readme.md")
    assert result == "Some title"


def test_extract_main_question_fallback_filename() -> None:
    """extract_main_question falls back to filename."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_main_question,
    )

    result = extract_main_question("No title here", "myfile.md")
    assert result == "myfile.md"


def test_extract_subject_found() -> None:
    """extract_subject finds the subject."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_subject,
    )

    assert extract_subject(_SAMPLE_MD) == "Informatyka"


def test_extract_subject_default() -> None:
    """extract_subject returns default."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_subject,
    )

    assert extract_subject("No subject here") == "Ogólne"


def test_extract_key_points() -> None:
    """extract_key_points extracts ### headers."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_key_points,
    )

    points = extract_key_points(_SAMPLE_MD)
    assert len(points) >= 1


def test_extract_key_points_empty() -> None:
    """extract_key_points returns empty for no answer section."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_key_points,
    )

    assert extract_key_points("No 📚 section") == []


def test_extract_definitions() -> None:
    """extract_definitions finds bold term definitions."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_definitions,
    )

    defs = extract_definitions(_SAMPLE_MD)
    assert isinstance(defs, list)
    # Should exclude Przykład and Uwaga
    for term, _ in defs:
        assert "Przykład" not in term
        assert "Uwaga" not in term


def test_clean_html_empty() -> None:
    """clean_html returns empty for empty input."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        clean_html,
    )

    assert clean_html("") == ""


def test_clean_html_formatting() -> None:
    """clean_html converts markdown to HTML."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        clean_html,
    )

    result = clean_html('**bold** *italic* "quote"\ttab')
    assert "<b>" in result
    assert "<i>" in result
    assert "&quot;" in result
    assert "\t" not in result


def test_process_file(sample_file: Path) -> None:
    """process_file extracts cards from a file."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        process_file,
    )

    cards = process_file(str(sample_file))
    assert len(cards) >= 1


def test_process_file_no_match(tmp_path: Path) -> None:
    """process_file with non-matching filename."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        process_file,
    )

    p = tmp_path / "readme.txt"
    p.write_text(_MINIMAL_MD, encoding="utf-8")
    cards = process_file(str(p))
    assert isinstance(cards, list)


def test_process_file_no_key_points(tmp_path: Path) -> None:
    """process_file returns empty when no key points."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        process_file,
    )

    p = tmp_path / "01-test.md"
    p.write_text(_FALLBACK_MD, encoding="utf-8")
    cards = process_file(str(p))
    assert isinstance(cards, list)


def test_extract_key_points_short_header() -> None:
    """extract_key_points skips short headers."""
    from python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 import (
        extract_key_points,
    )

    content = "## \U0001f4da Odpowied\u017a g\u0142\u00f3wna\n\n### 1. \n\n### Ab\n"
    assert extract_key_points(content) == []


def test_main_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() processes directory and writes output."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 as mod

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
    assert "#separator:tab" in content


def test_main_error_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() handles file processing errors."""
    import python_pkg.praca_magisterska_video.generate_images.generate_anki_v2 as mod

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

    def failing_process(filepath: str) -> list[dict[str, str]]:
        msg = "test error"
        raise ValueError(msg)

    monkeypatch.setattr(mod, "Path", fake_path)
    monkeypatch.setattr(mod, "process_file", failing_process)
    mod.main()
    assert out_file.exists()
