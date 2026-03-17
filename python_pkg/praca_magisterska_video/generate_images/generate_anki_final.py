#!/usr/bin/env python3
"""Generate comprehensive Anki flashcards from exam questions.

Creates tab-separated file for Anki import with proper HTML formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

MIN_HEADER_LENGTH = 3
MIN_MATCH_LENGTH = 10
MIN_BODY_LENGTH = 50
MIN_QA_LENGTH = 30
MAX_CONTENT_LENGTH = 300
MAX_ANSWER_LENGTH = 400
MAX_COMPARISON_ITEMS = 6


def clean_text(text: str) -> str:
    """Clean and format text for Anki."""
    if not text:
        return ""

    # Convert markdown formatting to HTML
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)

    # Handle special characters
    text = text.replace("\t", " ")
    text = text.replace('"', "&quot;")

    # Clean up whitespace but preserve intentional line breaks
    text = re.sub(r" +", " ", text)
    return text.strip()


def format_list(items: list[str], *, numbered: bool = False) -> str:
    """Format a list of items as HTML."""
    if not items:
        return ""

    tag = "ol" if numbered else "ul"
    html = f"<{tag}>"
    for item in items:
        cleaned = clean_text(item)
        if cleaned:
            html += f"<li>{cleaned}</li>"
    html += f"</{tag}>"
    return html


def _get_file_metadata(
    filepath: str,
) -> tuple[str, str, str]:
    """Extract metadata from file."""
    with Path(filepath).open(encoding="utf-8") as f:
        content = f.read()

    filename = Path(filepath).name
    match = re.match(r"(\d+)-(.+)\.md", filename)
    num = match.group(1) if match else "00"

    subj_match = re.search(r"Przedmiot:\s*(\w+)", content)
    subject = subj_match.group(1) if subj_match else "Ogólne"

    return num, subject, content


def _extract_main_question_card(
    content: str,
    base_tags: str,
) -> list[dict[str, str]]:
    """Extract the main exam question card."""
    q_match = re.search(
        r'## Pytanie\s*\n\s*\*\*["\']?(.+?)["\']?\*\*',
        content,
        re.DOTALL,
    )
    if not q_match:
        return []

    main_q = re.sub(r"\s+", " ", q_match.group(1).strip())
    answer_match = re.search(
        r"## 📚 Odpowiedź główna\s*\n(.+?)" r"(?=\n## [📚🎯]|\n---\s*\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not answer_match:
        return []

    answer_section = answer_match.group(1)
    headers = re.findall(
        r"^### (?:\d+\.\s*)?(.+)$",
        answer_section,
        re.MULTILINE,
    )
    headers = [h.strip() for h in headers if len(h.strip()) > MIN_HEADER_LENGTH][:6]

    if not headers:
        return []

    answer_html = "<b>Kluczowe zagadnienia:</b>" + format_list(headers)
    return [
        {
            "front": clean_text(main_q),
            "back": answer_html,
            "tags": f"{base_tags} pytanie_glowne",
        }
    ]


def _make_question_text(header: str) -> str:
    """Generate a question from a section header."""
    if "Definicja" in header or "Co to" in header:
        return f"Co to jest:" f" {header.replace('Definicja', '').strip()}?"
    if "Charakterystyka" in header:
        stripped = header.replace("Charakterystyka", "").strip()
        return f"Scharakteryzuj: {stripped}"
    if header.endswith("?"):
        return header
    return f"Omów: {header}"


def _extract_body_parts(body: str) -> list[str]:
    """Extract structured answer parts from a section body."""
    answer_parts: list[str] = []

    subheaders = re.findall(r"^#### (.+)$", body, re.MULTILINE)
    if subheaders:
        answer_parts.extend(subheaders[:4])

    bullets = re.findall(r"[-•]\s*\*\*([^*]+)\*\*[:\s-]*([^\n]+)?", body)
    for term, desc in bullets[:5]:
        if desc:
            answer_parts.append(f"<b>{term}</b>: {desc.strip()}")
        else:
            answer_parts.append(f"<b>{term}</b>")

    if not answer_parts:
        paras = [
            p.strip()
            for p in body.split("\n\n")
            if p.strip()
            and not p.strip().startswith("```")
            and not p.strip().startswith("|")
        ]
        if paras:
            first = paras[0]
            if len(first) > MAX_CONTENT_LENGTH:
                first = first[:MAX_CONTENT_LENGTH] + "..."
            answer_parts.append(first)

    return answer_parts


def _extract_subsection_cards(
    content: str,
    base_tags: str,
) -> list[dict[str, str]]:
    """Extract subsection detail cards."""
    cards: list[dict[str, str]] = []
    sections = re.findall(
        r"^### (?:\d+\.\s*)?(.+?)\n((?:(?!^###).)+)",
        content,
        re.MULTILINE | re.DOTALL,
    )

    for raw_header, raw_body in sections:
        header = raw_header.strip()
        body = raw_body.strip()

        if len(body) < MIN_BODY_LENGTH or header.lower().startswith("przykład"):
            continue

        answer_parts = _extract_body_parts(body)

        if answer_parts:
            question = _make_question_text(header)
            if len(answer_parts) > 1:
                answer_html = format_list(answer_parts)
            else:
                answer_html = clean_text(answer_parts[0])

            cards.append(
                {
                    "front": clean_text(question),
                    "back": answer_html,
                    "tags": f"{base_tags} szczegoly",
                }
            )

    return cards


def _extract_algo_cards(
    content: str,
    base_tags: str,
) -> list[dict[str, str]]:
    """Extract algorithm/formula cards."""
    cards: list[dict[str, str]] = []
    algo_patterns = [
        r"#### Złożoność(?:\s+czasowa)?\s*\n(.+?)(?=\n####|\n###|\Z)",
        r"Złożoność:\s*\*\*([^*]+)\*\*",
    ]

    for pattern in algo_patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for algo_match in matches[:2]:
            if len(algo_match) > MIN_MATCH_LENGTH:
                algo_context = re.search(
                    r"### (\d+\.\s*)?(.+?)(?=\n)",
                    content[: content.find(algo_match)],
                )
                if algo_context:
                    algo_name = algo_context.group(2).strip()
                    cards.append(
                        {
                            "front": (
                                "Jaka jest złożoność" f" algorytmu/metody: {algo_name}?"
                            ),
                            "back": clean_text(algo_match.strip()[:200]),
                            "tags": f"{base_tags} zlozonosc",
                        }
                    )
                    break

    return cards


def _extract_comparison_cards(
    content: str,
    base_tags: str,
    num: str,
) -> list[dict[str, str]]:
    """Extract comparison cards."""
    compare_match = re.search(
        r"## .*(Porównanie|Zestawienie|vs).*\n(.+?)(?=\n## |\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not compare_match:
        return []

    compare_section = compare_match.group(2)
    items = re.findall(
        r"\|\s*\*\*([^|*]+)\*\*\s*\|([^|]+)\|",
        compare_section,
    )
    if not items:
        return []

    comparison_html = "<table><tr><th>Aspekt</th><th>Wartość</th></tr>"
    for aspect, value in items[:MAX_COMPARISON_ITEMS]:
        comparison_html += (
            f"<tr><td>{clean_text(aspect)}</td>" f"<td>{clean_text(value)}</td></tr>"
        )
    comparison_html += "</table>"

    title_match = re.search(
        r"## .*(Porównanie|Zestawienie)" r".*?(\w+.*?(?:vs|i|oraz).*?\w+)",
        compare_match.group(0),
        re.IGNORECASE,
    )
    if not title_match:
        return []

    return [
        {
            "front": ("Porównaj kluczowe różnice" f" w temacie: pytanie {num}"),
            "back": comparison_html,
            "tags": f"{base_tags} porownanie",
        }
    ]


def _extract_qa_cards(
    content: str,
    base_tags: str,
) -> list[dict[str, str]]:
    """Extract Q&A practice cards."""
    cards: list[dict[str, str]] = []
    qa_section = re.search(
        r"## 🎓 Pytania.*?\n(.+?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not qa_section:
        return cards

    qa_content = qa_section.group(1)
    qas = re.findall(
        r"### Q\d+:?\s*[\"']?(.+?)[\"']?\s*\n" r".*?Odpowiedź:\s*\n?(.+?)(?=\n### |\Z)",
        qa_content,
        re.DOTALL,
    )
    for raw_q, raw_a in qas[:3]:
        question = re.sub(r"\s+", " ", raw_q.strip())
        answer = raw_a.strip()
        if len(answer) > MIN_QA_LENGTH:
            a_lines = answer.split("\n")
            a_short = "\n".join(a_lines[:5])
            if len(a_short) > MAX_ANSWER_LENGTH:
                a_short = a_short[:MAX_ANSWER_LENGTH] + "..."

            cards.append(
                {
                    "front": clean_text(question),
                    "back": clean_text(a_short).replace("\n", "<br>"),
                    "tags": f"{base_tags} egzamin_praktyka",
                }
            )

    return cards


def extract_from_file(filepath: str) -> list[dict[str, str]]:
    """Extract flashcard data from a markdown file."""
    num, subject, content = _get_file_metadata(filepath)
    base_tags = f"egzamin_magisterski pyt{num} {subject}"

    cards: list[dict[str, str]] = []
    cards.extend(_extract_main_question_card(content, base_tags))
    cards.extend(_extract_subsection_cards(content, base_tags))
    cards.extend(_extract_algo_cards(content, base_tags))
    cards.extend(_extract_comparison_cards(content, base_tags, num))
    cards.extend(_extract_qa_cards(content, base_tags))

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
            cards = extract_from_file(md_file)
            all_cards.extend(cards)
            logger.info("  -> %d cards", len(cards))
        except (ValueError, OSError) as e:
            logger.info("  -> ERROR: %s", e)

    # Remove potential duplicates (same front)
    seen = set()
    unique_cards = []
    for card in all_cards:
        if card["front"] not in seen:
            seen.add(card["front"])
            unique_cards.append(card)

    # Write output file
    with Path(output_file).open("w", encoding="utf-8") as f:
        # Anki headers
        f.write("#separator:tab\n")
        f.write("#html:true\n")
        f.write("#tags column:3\n")
        f.write("#deck:Egzamin Magisterski ISY\n")
        f.write("#notetype:Basic\n")
        f.write("\n")

        for card in unique_cards:
            # Ensure no tabs in content (would break parsing)
            front = card["front"].replace("\t", " ")
            back = card["back"].replace("\t", " ")
            tags = card["tags"]

            f.write(f"{front}\t{back}\t{tags}\n")

    logger.info("=" * 50)
    logger.info("Generated %d unique flashcards", len(unique_cards))
    logger.info("Saved to: %s", output_file)
    logger.info("=" * 50)
    logger.info("IMPORT INSTRUCTIONS:")
    logger.info("-" * 40)
    logger.info("Anki Desktop:")
    logger.info("  1. File -> Import")
    logger.info("  2. Select: anki_egzamin_magisterski.txt")
    logger.info("  3. Verify: Fields separated by Tab")
    logger.info("  4. Check: Allow HTML in fields")
    logger.info("  5. Click Import")
    logger.info("")
    logger.info("AnkiWeb / AnkiDroid:")
    logger.info("  1. First import on Anki Desktop")
    logger.info("  2. Click Sync to upload to AnkiWeb")
    logger.info("  3. Sync on mobile to download")


if __name__ == "__main__":
    main()
