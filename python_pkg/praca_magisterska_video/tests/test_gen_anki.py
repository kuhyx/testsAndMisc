"""Tests for Anki flashcard generators."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


# =====================================================================
# anki_approach_1
# =====================================================================
class TestAnkiApproach1:
    """Tests for anki_approach_1 module."""

    def test_clean_text_empty(self) -> None:
        from anki_approach_1 import clean_text

        assert clean_text("") == ""

    def test_clean_text_bold_italic(self) -> None:
        from anki_approach_1 import clean_text

        assert "<b>bold</b>" in clean_text("**bold**")
        assert "<i>italic</i>" in clean_text("*italic*")

    def test_clean_text_special_chars(self) -> None:
        from anki_approach_1 import clean_text

        result = clean_text('hello\t"world"  extra')
        assert "\t" not in result
        assert "&quot;" in result
        assert "  " not in result

    def test_extract_cards_full(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = (
            "Przedmiot: Informatyka\n"
            "## Pytanie\n"
            '**"Jakie są typy?"**\n'
            "## 📚 Odpowiedź główna\n"
            "### 1. Typ A\n"
            "### 2. Typ B\n"
            "### 3. Typ C\n"
            "some body text that is long enough to pass the len filter "
            "and it continues on with more words to exceed fifty chars.\n\n"
            "another paragraph for detail.\n"
        )
        f = tmp_path / "05-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert len(cards) >= 1
        assert cards[0]["tags"] == "egzamin pyt05 Informatyka"

    def test_extract_cards_no_match(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        f = tmp_path / "readme.md"
        f.write_text("Just some text\nNothing special here.", encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_extract_cards_no_question_match(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = (
            "### Header One\n"
            "Body text that is long enough to be valid here and there "
            "and it continues on with enough content to be over fifty.\n\n"
            "First paragraph detail text goes here across many chars.\n"
        )
        f = tmp_path / "readme.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        # Should get detail card with "00" as num
        assert any(c["tags"].startswith("egzamin pyt00") for c in cards)

    def test_extract_cards_short_body_skipped(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = "### Header One\nShort.\n"
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_extract_cards_code_block_skipped(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = (
            "### Header\n"
            "Body text that is long enough to pass the minimum "
            "length requirement of fifty characters easily here.\n\n"
            "```python\ndef foo(): pass\n```\n"
        )
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        # Should get a card using non-code paragraph
        assert len(cards) >= 1

    def test_main(self) -> None:
        from anki_approach_1 import main

        fake_md = (
            "## Pytanie\n"
            '**"Q1"**\n'
            "## 📚 Odpowiedź główna\n"
            "### A\n### B\n### C\n"
            "### Detail\n"
            "Long body text that is definitely more than one hundred "
            "characters in total to pass the strict filter applied by "
            "approach one which requires over 100 chars in back field.\n\n"
            "Another paragraph here.\n"
        )
        mock_file = MagicMock()
        mock_file.name = "01-test.md"

        with (
            patch.object(Path, "glob", return_value=[Path("/fake/01-test.md")]),
            patch.object(
                Path,
                "open",
                side_effect=lambda *_a, **_kw: StringIO(fake_md),
            ),
        ):
            main()

    def test_extract_cards_q_no_answer(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = 'Przedmiot: CS\n## Pytanie\n**"Main question"**\n'
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert not any("Main question" in c.get("front", "") for c in cards)

    def test_extract_cards_answer_no_headers(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = (
            "## Pytanie\n"
            '**"Q text"**\n'
            "## 📚 Odpowiedź główna\n"
            "Plain text without any headers at all.\n"
        )
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_extract_cards_paras_empty(self, tmp_path: Path) -> None:
        from anki_approach_1 import extract_cards

        md = (
            "### ValidSection\n"
            "```python\n"
            "code that is definitely exceeding fifty characters in length.\n"
            "```\n"
        )
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert not any("ValidSection" in c.get("front", "") for c in cards)

    def test_main_duplicate_fronts(self) -> None:
        from anki_approach_1 import main

        fake_md = (
            "## Pytanie\n"
            '**"Q"**\n'
            "## 📚 Odpowiedź główna\n"
            "### A\n### B\n### C\n"
            "### Detail\n"
            "Long body text that is more than one hundred characters "
            "to pass the strict filter in approach one and really "
            "needs many words to get past the filter threshold.\n\n"
            "Another paragraph.\n"
        )
        with (
            patch.object(
                Path,
                "glob",
                return_value=[Path("/f/01-t.md"), Path("/f/02-t.md")],
            ),
            patch.object(
                Path,
                "open",
                side_effect=lambda *_a, **_kw: StringIO(fake_md),
            ),
        ):
            main()


# =====================================================================
# anki_approach_2
# =====================================================================
class TestAnkiApproach2:
    """Tests for anki_approach_2 module."""

    def test_clean_text_empty(self) -> None:
        from anki_approach_2 import clean_text

        assert clean_text("") == ""

    def test_clean_text_formatting(self) -> None:
        from anki_approach_2 import clean_text

        assert "<b>x</b>" in clean_text("**x**")
        assert "<i>y</i>" in clean_text("*y*")

    def test_extract_structured_content_definitions(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = "#### Definicja\nThis is a definition text.\n"
        result = extract_structured_content(body)
        assert result is not None
        assert "Definicja" in result

    def test_extract_structured_content_bullets(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = "- **Term1**: Description of term\n- **Term2**: Another desc\n"
        result = extract_structured_content(body)
        assert result is not None
        assert "Term1" in result

    def test_extract_structured_content_bullets_no_desc(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = "- **OnlyTerm**\n- **OnlyTerm2**\n"
        result = extract_structured_content(body)
        assert result is not None
        assert "OnlyTerm" in result

    def test_extract_structured_content_key_value(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = "**Key1** - Value of key one here\n**Key2**: Value two\n"
        result = extract_structured_content(body)
        assert result is not None
        assert "Key1" in result

    def test_extract_structured_content_paragraphs_fallback(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = (
            "This is a long paragraph that acts as a fallback and contains "
            "more than thirty characters for sure.\n\n"
            "Second paragraph also long enough to pass the filter.\n"
        )
        result = extract_structured_content(body)
        assert result is not None

    def test_extract_structured_content_empty(self) -> None:
        from anki_approach_2 import extract_structured_content

        result = extract_structured_content("")
        assert result is None

    def test_extract_structured_content_code_table_skipped(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = "```python\ncode\n```\n\n| A | B |\n\nshort"
        result = extract_structured_content(body)
        assert result is None

    def test_extract_cards_full(self, tmp_path: Path) -> None:
        from anki_approach_2 import extract_cards

        md = (
            "Przedmiot: AI\n"
            "## Pytanie\n"
            '**"Q1"**\n'
            "## 📚 Odpowiedź główna\n"
            "#### Definicja\nSome definition text here.\n\n"
            "### 1. Section One\n"
            "Long body text that contains enough characters "
            "for the minimum body length of fifty characters to pass.\n\n"
            "- **BulletTerm**: Bullet description for detail\n"
        )
        f = tmp_path / "03-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert len(cards) >= 1

    def test_extract_cards_skip_example_and_quote(self, tmp_path: Path) -> None:
        from anki_approach_2 import extract_cards

        md = (
            "## Pytanie\n"
            '**"Q1"**\n'
            '### Przykład with "quotes"\n'
            "Body text that is definitely long enough to pass the minimum "
            "body length check of fifty.\n\n"
        )
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        # Przykład and quoted headers should be skipped
        assert not any("Przykład" in c.get("front", "") for c in cards)

    def test_extract_cards_no_answer(self, tmp_path: Path) -> None:
        from anki_approach_2 import extract_cards

        md = "## Pytanie\n**Q1**\nNo answer section here.\n"
        f = tmp_path / "readme.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_main(self) -> None:
        from anki_approach_2 import main

        fake_md = (
            "## Pytanie\n"
            '**"Q1"**\n'
            "## 📚 Odpowiedź główna\n"
            "#### Definicja\nDefinition here.\n"
        )
        with (
            patch.object(Path, "glob", return_value=[Path("/fake/01-test.md")]),
            patch.object(
                Path,
                "open",
                side_effect=lambda *_a, **_kw: StringIO(fake_md),
            ),
        ):
            main()

    def test_extract_structured_bullet_empty_desc(self) -> None:
        from anki_approach_2 import extract_structured_content

        body = "- **TermAlone**\n"
        result = extract_structured_content(body)
        assert result is not None
        assert "TermAlone" in result

    def test_extract_cards_q_no_answer(self, tmp_path: Path) -> None:
        from anki_approach_2 import extract_cards

        md = '## Pytanie\n**"Question"**\nNo answer section.\n'
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_extract_cards_answer_none(self, tmp_path: Path) -> None:
        from anki_approach_2 import extract_cards

        md = '## Pytanie\n**"Q"**\n## 📚 Odpowiedź główna\nshort\n'
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_extract_cards_section_answer_none(self, tmp_path: Path) -> None:
        from anki_approach_2 import extract_cards

        md = (
            "### ValidSection\n"
            "```python\n"
            "code that makes the body over fifty characters in length"
            " easily surpassing the minimum check.\n"
            "```\n"
        )
        f = tmp_path / "01-test.md"
        f.write_text(md, encoding="utf-8")
        cards = extract_cards(str(f))
        assert cards == []

    def test_main_duplicate_fronts(self) -> None:
        from anki_approach_2 import main

        fake_md = (
            '## Pytanie\n**"Q"**\n'
            "## 📚 Odpowiedź główna\n"
            "#### Definicja\nDefinition here.\n"
        )
        with (
            patch.object(
                Path,
                "glob",
                return_value=[Path("/f/01-t.md"), Path("/f/02-t.md")],
            ),
            patch.object(
                Path,
                "open",
                side_effect=lambda *_a, **_kw: StringIO(fake_md),
            ),
        ):
            main()


# =====================================================================
# anki_generator
# =====================================================================
