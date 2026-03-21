#!/usr/bin/env python3
"""Generate Anki flashcards with ACTUAL substantive answers, not just headers."""

from __future__ import annotations

import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

MIN_PARA_LENGTH = 20
MAX_PARA_LENGTH = 400
MIN_BODY_LENGTH = 80


def clean_text(text: str) -> str:
    """Clean text for Anki."""
    if not text:
        return ""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = text.replace("\t", " ")
    text = text.replace('"', "&quot;")
    text = re.sub(r" +", " ", text)
    return text.strip()


def extract_real_answer(content: str, section_name: str) -> str | None:
    """Extract actual content from a section, not just headers."""
    # Find the section
    pattern = rf"### (?:\d+\.\s*)?{re.escape(section_name)}\s*\n((?:(?!^### ).)+)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if not match:
        return None

    body = match.group(1).strip()

    # Extract meaningful content
    lines = []

    # Get subheaders with their first line of content
    subheader_pattern = r"#### ([^\n]+)\n([^\n#]+)"
    for sub_header, first_line in re.findall(subheader_pattern, body):
        lines.append(f"<b>{sub_header.strip()}</b>: {first_line.strip()}")

    # Get bullet points
    bullet_pattern = r"[-•]\s*\*\*([^*]+)\*\*[:\s-]*([^\n]*)"
    for term, desc in re.findall(bullet_pattern, body):
        if desc.strip():
            lines.append(f"• <b>{term.strip()}</b>: {desc.strip()}")
        else:
            lines.append(f"• <b>{term.strip()}</b>")

    # If no structured content, get paragraphs
    if not lines:
        paras = [
            p.strip()
            for p in body.split("\n\n")
            if p.strip() and not p.startswith("```") and not p.startswith("|")
        ]
        lines.extend(
            p
            for p in paras[:2]
            if len(p) > MIN_PARA_LENGTH and len(p) < MAX_PARA_LENGTH
        )

    return "<br>".join(lines[:6]) if lines else None


def _read_file_metadata(
    filepath: str | Path,
) -> tuple[str, str, str | None]:
    """Read file and extract metadata."""
    with Path(filepath).open(encoding="utf-8") as f:
        content = f.read()

    filename = Path(filepath).name
    match = re.match(r"(\d+)-(.+)\.md", filename)
    num = match.group(1) if match else "00"

    subj_match = re.search(r"Przedmiot:\s*(\w+)", content)
    subject = subj_match.group(1) if subj_match else "Ogólne"
    base_tags = f"egzamin_magisterski pyt{num} {subject}"

    q_match = re.search(
        r'## Pytanie\s*\n\s*\*\*["\']?(.+?)["\']?\*\*',
        content,
        re.DOTALL,
    )
    main_question = re.sub(r"\s+", " ", q_match.group(1).strip()) if q_match else None

    return content, base_tags, main_question


def _extract_automata_facts(content: str) -> list[str]:
    """Extract automata-specific facts."""
    parts: list[str] = []
    automata = [
        ("Automat Skończony", "FA"),
        ("Automat ze Stosem", "PDA"),
        ("Maszyna Turinga", "TM"),
    ]
    for name, abbrev in automata:
        pattern = rf"{name}.*?Rozpoznawana klasa języków" r"\s*\n\s*\*\*([^*]+)\*\*"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            parts.append(f"<b>{name} ({abbrev})</b>: {match.group(1).strip()}")
    return parts


def _extract_generic_facts(content: str) -> list[str]:
    """Extract generic definitions and summaries."""
    parts: list[str] = []
    key_patterns = [
        r"#### Definicja\s*\n([^\n#]+)",
        r"#### Charakterystyka\s*\n([^\n#]+)",
        r"\*\*Definicja[:\s]*\*\*\s*([^\n]+)",
    ]
    for pattern in key_patterns:
        parts.extend(
            found.strip()
            for found in re.findall(pattern, content)[:3]
            if len(found) > MIN_PARA_LENGTH
        )
    return parts


def _extract_first_paragraphs(content: str) -> list[str]:
    """Extract first substantive paragraphs from main answer."""
    main_answer = re.search(
        r"## 📚 Odpowiedź główna\s*\n(.+?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not main_answer:
        return []
    text = main_answer.group(1)
    paras = re.findall(r"\n\n([^#\n][^\n]{50,300})", text)
    return paras[:3]


def _build_main_card(
    content: str,
    main_question: str | None,
    base_tags: str,
) -> dict[str, str] | None:
    """Build the main question card."""
    if not main_question:
        return None

    answer_parts: list[str] = []
    if "automat" in main_question.lower() or "maszyn" in main_question.lower():
        answer_parts = _extract_automata_facts(content)

    if not answer_parts:
        answer_parts = _extract_generic_facts(content)

    if not answer_parts:
        answer_parts = _extract_first_paragraphs(content)

    if not answer_parts:
        return None

    answer = "<br><br>".join(clean_text(p) for p in answer_parts)
    return {
        "front": clean_text(main_question),
        "back": answer,
        "tags": f"{base_tags} pytanie_glowne",
    }


def _extract_section_content(body: str) -> list[str]:
    """Extract content lines from a section body."""
    answer_lines: list[str] = []

    def_match = re.search(
        r"#### Definicja[^\n]*\n([^\n#]+(?:\n[^\n#]+)?)",
        body,
    )
    if def_match:
        answer_lines.append(def_match.group(1).strip())

    char_match = re.search(
        r"#### Charakterystyka\s*\n((?:[-•][^\n]+\n?)+)",
        body,
    )
    if char_match:
        bullets = re.findall(
            r"[-•]\s*\*\*([^*]+)\*\*[:\s]*([^\n]*)",
            char_match.group(1),
        )
        for term, desc in bullets[:4]:
            answer_lines.append(
                f"• <b>{term}</b>: {desc.strip()}" if desc else f"• <b>{term}</b>"
            )

    if not answer_lines:
        bullets = re.findall(
            r"[-•]\s*\*\*([^*]+)\*\*[:\s]*([^\n]*)",
            body,
        )
        for term, desc in bullets[:5]:
            answer_lines.append(
                f"• <b>{term}</b>: {desc.strip()}" if desc else f"• <b>{term}</b>"
            )

    if not answer_lines:
        first_para = re.search(
            r"^([^#\n\-•|`][^\n]{30,250})",
            body,
            re.MULTILINE,
        )
        if first_para:
            answer_lines.append(first_para.group(1))

    return answer_lines


def _build_concept_cards(
    content: str,
    base_tags: str,
) -> list[dict[str, str]]:
    """Build concept cards from ### sections."""
    cards: list[dict[str, str]] = []
    sections = re.findall(
        r"^### (?:\d+\.\s*)?([^\n]+)\n((?:(?!^### ).)*)",
        content,
        re.MULTILINE | re.DOTALL,
    )

    for raw_header, raw_body in sections:
        header = raw_header.strip()
        body = raw_body.strip()

        if (
            len(body) < MIN_BODY_LENGTH
            or "Przykład" in header
            or "Mnemonic" in header
            or '"' in header
        ):
            continue

        answer_lines = _extract_section_content(body)
        if not answer_lines:
            continue

        question = header if header.endswith("?") else f"Wyjaśnij: {header}"
        answer = "<br>".join(clean_text(line) for line in answer_lines)
        cards.append(
            {
                "front": clean_text(question),
                "back": answer,
                "tags": f"{base_tags} szczegoly",
            }
        )

    return cards


def _build_qa_cards(
    content: str,
    base_tags: str,
) -> list[dict[str, str]]:
    """Build Q&A practice cards."""
    cards: list[dict[str, str]] = []
    qa_matches = re.findall(
        r'### Q\d+:\s*["\']?([^"\'?\n]+)\?*["\']?\s*\n'
        r".*?Odpowiedź:\s*\n(.+?)(?=\n### |\n## |\Z)",
        content,
        re.DOTALL,
    )

    for raw_question, raw_answer in qa_matches[:5]:
        question = raw_question.strip()
        answer_text = raw_answer.strip()

        answer_lines = answer_text.split("\n")
        clean_answer = [
            stripped
            for raw_line in answer_lines[:6]
            if (stripped := raw_line.strip())
            and not stripped.startswith("```")
            and not stripped.startswith("|")
        ]

        if clean_answer:
            cards.append(
                {
                    "front": clean_text(question + "?"),
                    "back": "<br>".join(clean_text(line) for line in clean_answer),
                    "tags": f"{base_tags} qa",
                }
            )

    return cards


def extract_cards(filepath: str | Path) -> list[dict[str, str]]:
    """Extract flashcards from a file."""
    content, base_tags, main_question = _read_file_metadata(filepath)

    cards: list[dict[str, str]] = []
    main_card = _build_main_card(content, main_question, base_tags)
    if main_card:
        cards.append(main_card)

    cards.extend(_build_concept_cards(content, base_tags))
    cards.extend(_build_qa_cards(content, base_tags))
    return cards


def main() -> None:
    """Main."""
    odpowiedzi_dir = Path("/home/kuchy/praca_magisterska/pytania/odpowiedzi")
    output_file = Path(
        "/home/kuchy/praca_magisterska/pytania/anki_egzamin_magisterski.txt"
    )

    all_cards = []

    for md_file in sorted(odpowiedzi_dir.glob("*.md")):
        logger.info("Processing: %s", md_file.name)
        try:
            cards = extract_cards(md_file)
            all_cards.extend(cards)
            logger.info("  -> %d cards", len(cards))
        except (ValueError, OSError):
            logger.exception("  -> Error processing file")

    # Remove duplicates
    seen = set()
    unique_cards = []
    for card in all_cards:
        key = card["front"][:100]
        if key not in seen:
            seen.add(key)
            unique_cards.append(card)

    # Write file
    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write("#separator:Tab\n")
        f.write("#html:true\n")
        f.write("#notetype:Basic\n")
        f.write("#deck:Egzamin Magisterski ISY\n")
        f.write("#columns:Front\tBack\tTags\n")
        f.write("#tags column:3\n")
        f.write("\n")

        for card in unique_cards:
            front = card["front"].replace("\t", " ")
            back = card["back"].replace("\t", " ")
            tags = card["tags"]
            f.write(f"{front}\t{back}\t{tags}\n")

    logger.info(
        "Generated %d unique cards from %d total",
        len(unique_cards),
        len(all_cards),
    )
    logger.info("Output: %s", output_file)


if __name__ == "__main__":
    main()
