"""Three pillars and observer card diagrams."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np

from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
    _BAND_HEIGHTS,
    BG,
    DPI,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    OUTPUT_DIR,
    draw_arrow,
)

_logger = logging.getLogger(__name__)

# ============================================================
# 3. Three Pillars of Cataloguing
# ============================================================
def generate_three_pillars() -> None:
    """Generate three pillars of cataloguing diagram."""
    fig, ax = plt.subplots(figsize=(8.27, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "Jak są katalogowane wzorce? — Trzy filary",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=15,
    )

    # Roof / banner
    roof_pts = np.array([[1, 5.5], [6, 6.8], [11, 5.5]])
    roof = plt.Polygon(
        roof_pts,
        closed=True,
        lw=2,
        edgecolor=LN,
        facecolor=GRAY4,
    )
    ax.add_patch(roof)
    ax.text(
        6,
        6.0,
        "KATALOGOWANIE WZORCÓW",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )

    # Three pillars
    pillars = [
        (
            1.3,
            "1. SZABLON\nOPISU",
            "Każdy wzorzec ma\nte same pola:\n"
            "Nazwa → Problem\n→ Siły → Rozwiązanie\n"
            "→ Konsekwencje",
            "Analogia:\nformatka\nencyklopedii",
        ),
        (
            4.8,
            "2. KLASYFIKACJA\nWIELOOSIOWA",
            "Osie podziału:\n"
            "• Skala (arch/proj/idiom)\n"
            "• Domena problemu\n"
            "• Atrybut jakościowy\n"
            "• Domena zastosowania",
            "Analogia:\nkategorie\nw bibliotece",
        ),
        (
            8.3,
            "3. JĘZYK\nWZORCÓW",
            "Wzorce referują się\nwzajemnie tworząc\n"
            "sieć/graf:\nA → wymaga → B\n"
            "B → wariant → C",
            "Analogia:\n\u201ezobacz te\u017c\u201d\n"
            "w encyklopedii",
        ),
    ]

    for px, title, desc, analogy in pillars:
        pw, ph = 2.8, 5.0
        py = 0.5

        # Pillar rectangle
        rect = FancyBboxPatch(
            (px, py),
            pw,
            ph,
            boxstyle="round,pad=0.1",
            lw=1.8,
            edgecolor=LN,
            facecolor="white",
        )
        ax.add_patch(rect)

        # Title
        ax.text(
            px + pw / 2,
            py + ph - 0.55,
            title,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

        # Horizontal line under title
        ax.plot(
            [px + 0.2, px + pw - 0.2],
            [py + ph - 1.0, py + ph - 1.0],
            color=LN,
            lw=0.8,
        )

        # Description
        ax.text(
            px + pw / 2,
            py + ph / 2 - 0.3,
            desc,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            linespacing=1.4,
        )

        # Analogy box at bottom
        analogy_rect = FancyBboxPatch(
            (px + 0.2, py + 0.15),
            pw - 0.4,
            1.0,
            boxstyle="round,pad=0.06",
            lw=0.8,
            edgecolor=GRAY3,
            facecolor=GRAY1,
        )
        ax.add_patch(analogy_rect)
        ax.text(
            px + pw / 2,
            py + 0.65,
            analogy,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontstyle="italic",
            color="#555555",
        )

    fig.tight_layout()
    out = str(Path(OUTPUT_DIR) / "q14_three_pillars.png")
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", out)


# ============================================================
# 4. Filled-in Observer Pattern Card
# ============================================================
def _get_observer_band_height(index: int) -> float:
    """Return band height for the given field index."""
    return _BAND_HEIGHTS[index]


def generate_observer_card_filled() -> None:
    """Generate filled-in Observer pattern card diagram."""
    fig, ax = plt.subplots(figsize=(8.27, 8.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "Wypełniona karta wzorca — Observer (GoF)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=15,
    )

    # Main card outline
    card_x, card_y, card_w, card_h = 0.8, 0.3, 8.4, 9.2
    card = FancyBboxPatch(
        (card_x, card_y),
        card_w,
        card_h,
        boxstyle="round,pad=0.15",
        lw=2.5,
        edgecolor=LN,
        facecolor=GRAY4,
    )
    ax.add_patch(card)

    # Fields with actual Observer content
    fields = [
        ("Na", "NAZWA", "Observer", GRAY2, True),
        (
            "P",
            "PROBLEM",
            "Obiekt (Subject) zmienia stan → wielu"
            " zależnych\n"
            "obiektów musi zareagować, ale Subject nie\n"
            "powinien znać ich konkretnych typów.",
            GRAY1,
            False,
        ),
        (
            "Si",
            "SIŁY",
            "• loose coupling (nie znać obserwatorów"
            " z nazwy)\n"
            "  vs koszt powiadomień"
            " (N obserwatorów = N wywołań)\n"
            "• otwartość na rozszerzenia"
            " vs złożoność debugowania",
            "white",
            False,
        ),
        (
            "Ro",
            "ROZWIĄZANIE",
            "Subject przechowuje listę Observer.\n"
            "Metody: attach(o), detach(o), notify().\n"
            "notify() iteruje po liście i woła update()\n"
            "na każdym obserwatorze.",
            GRAY1,
            False,
        ),
        (
            "Ko",
            "KONSEKWENCJE",
            "(+) Luźne wiązanie — Subject ↔ Observer\n"
            "(+) Nowi obserwatorzy bez zmian w Subject\n"
            "(-) Kaskada powiadomień może być kosztowna\n"
            "(-) Memory leaks jeśli nie detach()",
            "white",
            False,
        ),
    ]

    band_x = card_x + 0.3
    band_w = card_w - 0.6
    start_y = card_y + card_h - 0.65

    for i, (abbr, title, content, fill, is_title_field) in enumerate(
        fields
    ):
        band_h = _get_observer_band_height(i)

        by = start_y - sum(
            _get_observer_band_height(j) + 0.15 for j in range(i)
        )

        # Abbreviation circle
        circle = plt.Circle(
            (band_x + 0.35, by + band_h / 2),
            0.28,
            lw=1.5,
            edgecolor=LN,
            facecolor=GRAY3,
        )
        ax.add_patch(circle)
        ax.text(
            band_x + 0.35,
            by + band_h / 2,
            abbr,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
        )

        # Field box
        fx = band_x + 0.8
        fw = band_w - 0.8
        rect = FancyBboxPatch(
            (fx, by),
            fw,
            band_h,
            boxstyle="round,pad=0.06",
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)

        if is_title_field:
            ax.text(
                fx + fw / 2,
                by + band_h / 2,
                f"{title}: {content}",
                ha="center",
                va="center",
                fontsize=12,
                fontweight="bold",
            )
        else:
            ax.text(
                fx + 0.15,
                by + band_h - 0.2,
                title,
                ha="left",
                va="center",
                fontsize=FS,
                fontweight="bold",
            )
            ax.text(
                fx + 0.15,
                by + band_h / 2 - 0.15,
                content,
                ha="left",
                va="center",
                fontsize=FS_SMALL,
                family="monospace",
                linespacing=1.3,
            )

        # Arrow
        if i < len(fields) - 1:
            draw_arrow(
                ax,
                band_x + 0.35,
                by - 0.02,
                band_x + 0.35,
                by - 0.13,
                lw=1.0,
            )

    # Extra info at bottom
    extra_y = 0.55
    extras = [
        "Powiązane: Mediator (centralizuje),"
        " Pub/Sub (rozproszony),"
        " MVC (View = Observer)",
        "Znane użycia: Java Swing listeners,"
        " C# event/delegate,"
        " React useState, DOM addEventListener",
    ]
    for j, txt in enumerate(extras):
        ax.text(
            card_x + card_w / 2,
            extra_y + (1 - j) * 0.25,
            txt,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontstyle="italic",
            color="#444444",
        )

    fig.tight_layout()
    out = str(Path(OUTPUT_DIR) / "q14_observer_card_filled.png")
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", out)
