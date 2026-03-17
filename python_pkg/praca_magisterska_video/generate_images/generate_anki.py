#!/usr/bin/env python3
"""Generate Anki flashcards from exam questions in odpowiedzi/ folder.

Creates a tab-separated file compatible with Anki import.
"""

from __future__ import annotations

import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

MIN_BODY_LENGTH = 50
MIN_DEFINITION_LENGTH = 20
MAX_DEFINITION_LENGTH = 200
MIN_BULLET_COUNT = 5
MIN_SUBSECTION_LENGTH = 5
MIN_FORMULA_LENGTH = 20


def _get_metadata(
    filepath: str,
) -> tuple[str, str, str, str, str]:
    """Extract metadata from file."""
    with Path(filepath).open(encoding="utf-8") as f:
        content = f.read()

    filename = Path(filepath).name
    match = re.match(r"(\d+)-(.+)\.md", filename)
    if match:
        num = match.group(1)
        topic = match.group(2).replace("-", "_")
    else:
        num = "00"
        topic = "unknown"

    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Unknown"

    question_match = re.search(
        r'## Pytanie\s*\n\s*\*\*["\']?(.+?)["\']?\*\*',
        content,
        re.DOTALL,
    )
    if question_match:
        main_question = question_match.group(1).strip()
        main_question = re.sub(r"\s+", " ", main_question)
    else:
        main_question = title

    return num, topic, title, main_question, content


def _extract_main_card(
    content: str,
    main_question: str,
    subject: str,
    num: str,
    topic: str,
) -> list[dict[str, str]]:
    """Extract the main question card."""
    answer_parts: list[str] = []

    main_answer = re.search(
        r"## 📚 Odpowiedź główna\s*\n(.+?)" r"(?=\n## |\n---\s*\n## |\Z)",
        content,
        re.DOTALL,
    )
    if main_answer:
        answer_text = main_answer.group(1)
        headers = re.findall(r"### (.+)", answer_text)
        answer_parts.extend(f"• {h}" for h in headers[:5])

    definitions = re.findall(r"\*\*([^*]+)\*\*\s*[--:]\s*([^*\n]+)", content)
    for term, definition in definitions[:3]:
        if (
            len(definition) > MIN_DEFINITION_LENGTH
            and len(definition) < MAX_DEFINITION_LENGTH
        ):
            answer_parts.append(f"• {term}: {definition.strip()}")

    if not answer_parts:
        return []

    answer_html = "<br>".join(answer_parts[:8])
    return [
        {
            "question": main_question,
            "answer": answer_html,
            "tags": (f"egzamin_magisterski pytanie_{num}" f" {subject} {topic}"),
        }
    ]


def _extract_subsection_answer(body_clean: str) -> str | None:
    """Extract answer text from a subsection body."""
    bullets = re.findall(r"[-•]\s*\*\*(.+?)\*\*[:\s]*([^\n]+)?", body_clean)
    if bullets:
        return "<br>".join(
            f"• {b[0]}: {b[1].strip()}" if b[1] else f"• {b[0]}"
            for b in bullets[:MIN_BULLET_COUNT]
        )

    paragraphs = [
        p.strip()
        for p in body_clean.split("\n\n")
        if p.strip() and not p.startswith("```") and not p.startswith("|")
    ]
    if paragraphs:
        first_para = paragraphs[0]
        first_para = re.sub(r"\*\*(.+?)\*\*", r"\1", first_para)
        first_para = re.sub(r"\*(.+?)\*", r"\1", first_para)
        return first_para[:400]

    return None


def _extract_sub_cards(
    content: str,
    title: str,
    subject: str,
    num: str,
    topic: str,
) -> list[dict[str, str]]:
    """Extract sub-concept cards."""
    cards: list[dict[str, str]] = []
    subsections = re.findall(
        r"### (\d+\.\s+)?(.+?)\n\n(.+?)" r"(?=\n### |\n## |\n---|\Z)",
        content,
        re.DOTALL,
    )

    for _, header, body in subsections:
        if len(header) < MIN_SUBSECTION_LENGTH or header.startswith("Przykład"):
            continue

        body_clean = body.strip()
        if len(body_clean) < MIN_BODY_LENGTH:
            continue

        answer_text = _extract_subsection_answer(body_clean)
        if not answer_text:
            continue

        sub_question = f"Co to jest {header}?" if not header.endswith("?") else header

        if any(kw in header for kw in ("Charakterystyka", "Definicja", "Właściwości")):
            parent = title.replace("Pytanie", "").strip(": 0123456789")
            sub_question = f"{header} - {parent}"

        cards.append(
            {
                "question": sub_question,
                "answer": answer_text,
                "tags": (
                    f"egzamin_magisterski pytanie_{num}" f" {subject} {topic} szczegoly"
                ),
            }
        )

    return cards


def _extract_formula_cards(
    content: str,
    subject: str,
    num: str,
) -> list[dict[str, str]]:
    """Extract formula/definition cards."""
    cards: list[dict[str, str]] = []
    formulas = re.findall(
        r"\*\*([A-Za-z\s]+"
        r"(?:formuła|wzór|twierdzenie|definicja|lemat))"
        r"\*\*[:\s]*\n?(.+?)(?=\n\n|\n\*\*|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    for formula_name, formula_content in formulas:
        if len(formula_content) > MIN_FORMULA_LENGTH:
            cards.append(
                {
                    "question": f"Podaj {formula_name.strip()}",
                    "answer": formula_content.strip()[:300],
                    "tags": (
                        f"egzamin_magisterski pytanie_{num}" f" {subject} formuly"
                    ),
                }
            )

    return cards


def extract_question_and_answer(
    filepath: str,
) -> list[dict[str, str]]:
    """Extract main question and key answer points from a markdown file."""
    num, topic, title, main_question, content = _get_metadata(filepath)

    subject_match = re.search(r"Przedmiot:\s*(\w+)", content)
    subject = subject_match.group(1) if subject_match else "Ogólne"

    cards: list[dict[str, str]] = []
    cards.extend(_extract_main_card(content, main_question, subject, num, topic))
    cards.extend(_extract_sub_cards(content, title, subject, num, topic))
    cards.extend(_extract_formula_cards(content, subject, num))

    return cards


def clean_for_anki(text: str) -> str:
    """Clean text for Anki import - escape special characters."""
    # Replace tabs with spaces
    text = text.replace("\t", "    ")
    # Convert markdown formatting to HTML
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # Handle newlines - convert to <br> for Anki
    text = text.replace("\n", "<br>")
    # Remove multiple <br>
    text = re.sub(r"(<br>)+", "<br>", text)
    # Remove leading/trailing <br>
    text = re.sub(r"^<br>|<br>$", "", text)
    # Escape quotes in a way that works with tab-separated
    text = text.replace('"', "&quot;")
    return text.strip()


def main() -> None:
    """Main."""
    odpowiedzi_dir = Path("/home/kuchy/praca_magisterska/pytania/odpowiedzi")
    output_file = Path(
        "/home/kuchy/praca_magisterska/pytania/anki_egzamin_magisterski.txt"
    )

    all_cards = []

    # Process each file
    for md_file in sorted(odpowiedzi_dir.glob("*.md")):
        logger.info("Processing: %s", md_file.name)
        try:
            cards = extract_question_and_answer(md_file)
            all_cards.extend(cards)
            logger.info("  -> Extracted %d cards", len(cards))
        except (ValueError, OSError) as e:
            logger.info("  -> Error: %s", e)

    # Write Anki file with headers
    with Path(output_file).open("w", encoding="utf-8") as f:
        # Anki file headers
        f.write("#separator:tab\n")
        f.write("#html:true\n")
        f.write("#columns:Front\tBack\tTags\n")
        f.write("#deck:Egzamin Magisterski ISY\n")
        f.write("#notetype:Basic\n")
        f.write("\n")

        for card in all_cards:
            front = clean_for_anki(card["question"])
            back = clean_for_anki(card["answer"])
            tags = card["tags"]
            f.write(f"{front}\t{back}\t{tags}\n")

    logger.info("Created %d flashcards", len(all_cards))
    logger.info("Output: %s", output_file)
    logger.info("To import into Anki:")
    logger.info("1. Open Anki -> File -> Import")
    logger.info("2. Select the .txt file")
    logger.info("3. Verify 'Allow HTML' is checked")
    logger.info("4. Click Import")


if __name__ == "__main__":
    main()
