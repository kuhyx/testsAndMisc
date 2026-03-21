"""Tests for generate_images/anki_generator.py (part 3): remaining coverage gaps."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Markdown where detail sections have '"' and "Mnemonic" headers for skip branches
_MD_MNEMONIC_QUOTE = """\
# Pytanie 05: Special Headers

Przedmiot: Fizyka

## Pytanie

**"Explain special headers?"**

## 📚 Odpowiedź główna

### 1. Valid concept with content

#### Definicja
A definition text here that is long enough to be valid content.

- **ValidTerm**: Some description text here that tests branch
- **NoDescTerm**

### "Quoted header" section
Body content that is long enough to be over fifty characters for the threshold here.

### Mnemonic trick section
Body content that is long enough to be over fifty characters for the threshold too.

### 2. Tiny
X.
"""

# Markdown with no "📚 Odpowiedź główna" section
_MD_NO_ANSWER_SECTION = """\
# Pytanie 06: No Answer

Przedmiot: Chemia

## Pytanie

**"What is this question about?"**

## Some other section

Just random text here with no main answer section.
"""

# Markdown where ALL answer section headers should be skipped
_MD_ALL_SKIPPED = """\
# Pytanie 07: All Skipped

Przedmiot: Bio

## Pytanie

**"Describe all skipped?"**

## 📚 Odpowiedź główna

### Przykład showing example case
Body that is long enough to pass min body length threshold for sure.

### "Quoted" header here
Body that is long enough to pass min body length threshold for sure too.

### Mnemonic recall technique
Body that is long enough to pass min body length threshold for sure also.
"""

# Markdown with multiple key-value patterns for kv loop iteration
_MD_KV_MULTI = """\
# Pytanie 08: KV Patterns

Przedmiot: Matematyka

## Pytanie

**'Describe key-value patterns?'**

## 📚 Odpowiedź główna

### 1. Section with only KV

**First concept** -- description that is over ten characters total here
**Second concept** -- another long description that also matches kv regex
**Third concept** -- and one more description to test multiple iterations

### 2. Fallback section

Some paragraph content that is long enough to be captured as a nice fallback.

Another paragraph also long enough for extraction purposes and testing.
"""


@pytest.fixture
def mnemonic_file(tmp_path: Path) -> Path:
    """MD file with Mnemonic and quoted headers."""
    p = tmp_path / "05-special-headers.md"
    p.write_text(_MD_MNEMONIC_QUOTE, encoding="utf-8")
    return p


@pytest.fixture
def no_answer_file(tmp_path: Path) -> Path:
    """MD with main question but no answer section."""
    p = tmp_path / "06-no-answer.md"
    p.write_text(_MD_NO_ANSWER_SECTION, encoding="utf-8")
    return p


@pytest.fixture
def all_skipped_file(tmp_path: Path) -> Path:
    """MD where all headers should be skipped."""
    p = tmp_path / "07-all-skipped.md"
    p.write_text(_MD_ALL_SKIPPED, encoding="utf-8")
    return p


@pytest.fixture
def kv_file(tmp_path: Path) -> Path:
    """MD with multiple key-value patterns."""
    p = tmp_path / "08-kv-patterns.md"
    p.write_text(_MD_KV_MULTI, encoding="utf-8")
    return p


# --- extract_structured_content branch tests ---


def test_structured_content_bullet_no_desc() -> None:
    """Bullet with empty desc hits the else branch (line 114)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    body = (
        "#### Definicja\nDef text here.\n\n"
        "- **WithDesc**: has a description\n"
        "- **NoDesc**\n"
    )
    result = extract_structured_content(body)
    assert result is not None
    assert "NoDesc" in result


def test_structured_content_kv_loop_multiple() -> None:
    """Key-value loop iterates multiple times (121->119)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_structured_content,
    )

    # Single bullet gives parts < MIN_PARTS_THRESHOLD, so kv fallback triggers
    body = (
        "- **One**: single item\n\n"
        "**Alpha** -- description of alpha that is long enough\n"
        "**Beta** -- description of beta concept long enough\n"
        "**Gamma** -- description of gamma concept long enough\n"
    )
    result = extract_structured_content(body)
    assert result is not None


# --- extract_cards_better skip branches ---


def test_cards_better_skip_quoted_and_mnemonic(mnemonic_file: Path) -> None:
    """Sections with quote/Mnemonic in header are skipped (151->163, 153->163)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_better,
    )

    cards = extract_cards_better(str(mnemonic_file))
    for card in cards:
        assert "Quoted" not in card["front"]
        assert "Mnemonic" not in card["front"]


def test_cards_better_structured_returns_none(tmp_path: Path) -> None:
    """Section where extract_structured_content returns None."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_better,
    )

    md = """\
# Pytanie 09: None content

Przedmiot: Test

## Pytanie

**"Q?"**

## 📚 Odpowiedź główna

### Valid Section Name

```python
only_code_block_here_that_is_long_enough_to_pass_body = True
```
"""
    p = tmp_path / "09-empty.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_cards_better(str(p))
    assert isinstance(cards, list)


# --- extract_cards_basic skip branches ---


def test_cards_basic_empty_paras(tmp_path: Path) -> None:
    """Section in extract_cards_basic with no extractable paragraphs (238->227)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_basic,
    )

    md = """\
# Pytanie 10: No Paras

Przedmiot: Test

## Pytanie

**"No para test?"**

## 📚 Odpowiedź główna

### Header1
Content

### Valid Section Name With Enough Length

```python
only_code_block_here_that_is_long_enough_to_pass_length_threshold = True
another_line_here_to_make_body_long_enough_for_sure_past_fifty_chars = True
```
"""
    p = tmp_path / "10-noparas.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_cards_basic(str(p))
    assert isinstance(cards, list)


def test_cards_basic_loop_continue(tmp_path: Path) -> None:
    """Loop in extract_cards_basic continues past skipped sections (179->168)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_cards_basic,
    )

    md = """\
# Pytanie 11: Loop Continue

Przedmiot: Test

## Pytanie

**"Loop test?"**

## 📚 Odpowiedź główna

### 1. First valid section
Content here that is long enough to be over body threshold for paragraph.

### Przykład skip this section
Body that is long enough but starts with Przykład, so it is skipped.

### 2. Second valid section
More content here that is also long enough for extraction testing.
"""
    p = tmp_path / "11-loop.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_cards_basic(str(p))
    assert isinstance(cards, list)


# --- extract_main_only branches ---


def test_main_only_no_answer_section(no_answer_file: Path) -> None:
    """No answer section -> answer_match is None (293->312)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_main_only,
    )

    cards = extract_main_only(str(no_answer_file))
    assert cards == []


def test_main_only_all_skipped_headers(all_skipped_file: Path) -> None:
    """All headers skipped -> empty answer_parts -> return [] (316)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_main_only,
    )

    cards = extract_main_only(str(all_skipped_file))
    assert cards == []


def test_main_only_skip_mnemonic_and_quote(tmp_path: Path) -> None:
    """Headers with Mnemonic and quote skipped (203->222, 207->222)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_main_only,
    )

    md = """\
# Pytanie 12: Header Skips

Przedmiot: Test

## Pytanie

**"Test header skips?"**

## 📚 Odpowiedź główna

### Mnemonic for recall
- **Trick**: Memory trick description here.

### "Quoted" important header
- **Quote**: Information inside quotes.

### 1. Valid concept here
- **Term**: Valid description of the term for extraction.
"""
    p = tmp_path / "12-skips.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_main_only(str(p))
    # Only the valid concept should produce a key_point
    assert isinstance(cards, list)


def test_main_only_key_point_none(tmp_path: Path) -> None:
    """_extract_key_point returns None for all headers -> return [] (316)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        extract_main_only,
    )

    md = """\
# Pytanie 13: Key Point None

Przedmiot: Test

## Pytanie

**"Key point test?"**

## 📚 Odpowiedź główna

### Valid Header
short
"""
    p = tmp_path / "13-keynone.md"
    p.write_text(md, encoding="utf-8")
    cards = extract_main_only(str(p))
    assert cards == []


# --- _extract_key_point branch ---


def test_key_point_multiple_bullets() -> None:
    """Multiple bullets in _extract_key_point (238->227 loop continuation)."""
    from python_pkg.praca_magisterska_video.generate_images.anki_generator import (
        _extract_key_point,
    )

    body = "- **First**: desc1\n- **Second**: desc2\n- **Third**: desc3\n"
    result = _extract_key_point(body)
    assert result is not None
    assert "First" in result


# --- generate_anki function (lines 369-413) ---


def test_generate_anki_function(tmp_path: Path) -> None:
    """generate_anki with patched paths exercises function body."""
    import python_pkg.praca_magisterska_video.generate_images.anki_generator as mod

    cards = [
        {"front": "Q1", "back": "A" * 200, "tags": "t1"},
        {"front": "Q2", "back": "B" * 30, "tags": "t2"},
        {"front": "Q1", "back": "A" * 200, "tags": "t1"},
    ]

    real_path = Path

    def fake_path(*args: object) -> Path:
        s = str(args[0]) if args else ""
        if "/home/kuchy/" in s:
            return tmp_path / real_path(s).name
        return real_path(s)

    with (
        patch.object(mod, "Path", side_effect=fake_path),
        patch.object(mod, "_collect_cards", return_value=cards),
    ):
        result = mod.generate_anki()

    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "#separator:Tab" in content
    assert content.count("Q1") == 1


def test_generate_anki_with_all_flags(tmp_path: Path) -> None:
    """generate_anki with filter+extract+main flags."""
    import python_pkg.praca_magisterska_video.generate_images.anki_generator as mod

    cards = [{"front": "Q", "back": "A" * 200, "tags": "t"}]

    real_path = Path

    def fake_path(*args: object) -> Path:
        s = str(args[0]) if args else ""
        if "/home/kuchy/" in s:
            return tmp_path / real_path(s).name
        return real_path(s)

    with (
        patch.object(mod, "Path", side_effect=fake_path),
        patch.object(mod, "_collect_cards", return_value=cards),
    ):
        result = mod.generate_anki(
            use_filter=True,
            use_better_extract=True,
            main_only=True,
        )

    assert result.exists()
    assert "filter_extract_main" in result.name
