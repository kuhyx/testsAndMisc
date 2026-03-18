"""Pattern template and catalog map diagrams."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
    BG,
    DPI,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OUTPUT_DIR,
    draw_arrow,
)

_logger = logging.getLogger(__name__)


def generate_pattern_template() -> None:
    """Generate pattern template diagram with NaPSiRoKo mnemonic."""
    fig, ax = plt.subplots(figsize=(8.27, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "Szablon opisu wzorca \u2014 \u201eNaPSiRoKo\u201d",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=15,
    )

    # Main card outline
    card_x, card_y, card_w, card_h = 1.5, 0.5, 7, 7
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

    # Title of card
    ax.text(
        card_x + card_w / 2,
        card_y + card_h - 0.35,
        "KARTA WZORCA",
        ha="center",
        va="center",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    # Fields as horizontal bands
    fields = [
        ("Na", "NAZWA", "Layered, Observer, Microservices", GRAY1),
        (
            "P",
            "PROBLEM / KONTEKST",
            "Kiedy stosować? Jaki problem rozwiązuje?",
            "white",
        ),
        (
            "Si",
            "SIŁY (forces)",
            "Konkurencyjne wymagania do pogodzenia\n" "(np. testowalność vs wydajność)",
            GRAY1,
        ),
        ("Ro", "ROZWIĄZANIE", "Struktura, diagram, zachowanie", "white"),
        (
            "Ko",
            "KONSEKWENCJE",
            "Tradeoffs: co zyskujemy, co tracimy",
            GRAY1,
        ),
    ]

    band_x = card_x + 0.3
    band_w = card_w - 0.6
    band_h = 1.05
    start_y = card_y + card_h - 1.1

    for i, (abbr, title, desc, fill) in enumerate(fields):
        by = start_y - i * (band_h + 0.15)

        # Abbreviation circle on the left
        circle = plt.Circle(
            (band_x + 0.35, by + band_h / 2),
            0.28,
            lw=1.5,
            edgecolor=LN,
            facecolor=GRAY2,
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
        ax.text(
            fx + 0.15,
            by + band_h - 0.25,
            title,
            ha="left",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )
        ax.text(
            fx + 0.15,
            by + 0.25,
            desc,
            ha="left",
            va="center",
            fontsize=FS_SMALL,
            fontstyle="italic",
            color="#444444",
        )

        # Arrow connecting fields
        if i < len(fields) - 1:
            draw_arrow(
                ax,
                band_x + 0.35,
                by - 0.02,
                band_x + 0.35,
                by - 0.13,
                lw=1.0,
            )

    # Extra fields note at bottom
    ax.text(
        card_x + card_w / 2,
        card_y + 0.25,
        "+ Powiązane wzorce  •  Znane zastosowania  •  Warianty",
        ha="center",
        va="center",
        fontsize=FS_SMALL,
        fontstyle="italic",
    )

    # Mnemonic reminder on the right
    ax.text(
        9.8,
        4,
        "Mnemonik:\nNaPSiRoKo",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        rotation=90,
        color="#666666",
    )

    fig.tight_layout()
    out = str(Path(OUTPUT_DIR) / "q14_pattern_template.png")
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", out)


# ============================================================
# 2. Catalog Classification Map
# ============================================================
def generate_catalog_map() -> None:
    """Generate catalog classification map diagram."""
    fig, ax = plt.subplots(figsize=(8.27, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "Mapa katalog\u00f3w wzorc\u00f3w \u2014"
        " \u201ePawe\u0142 Gra\u0142 Efektownie"
        " Pod Chmurami\u201d",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=15,
    )

    # Y-axis: Scale (architectural -> design -> idiom)
    ax.text(
        0.3,
        7.8,
        "SKALA",
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="center",
        rotation=90,
    )
    ax.annotate(
        "",
        xy=(0.3, 2.0),
        xytext=(0.3, 7.5),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )

    scale_labels = [
        (7.0, "Architektoniczny\n(cały system)"),
        (5.0, "Projektowy\n(klasa/obiekt)"),
        (3.0, "Idiomatyczny\n(linia kodu)"),
    ]
    for sy, label in scale_labels:
        ax.text(
            1.0,
            sy,
            label,
            fontsize=FS_SMALL,
            ha="left",
            va="center",
            fontstyle="italic",
        )
        ax.plot([0.15, 0.45], [sy, sy], color=GRAY3, lw=0.8, ls="--")

    # X-axis: Domain
    ax.text(
        6.5,
        1.2,
        "DOMENA ZASTOSOWANIA",
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="center",
    )
    ax.annotate(
        "",
        xy=(11.5, 1.5),
        xytext=(2.0, 1.5),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )

    # Catalog boxes positioned by scale and domain
    catalogs = [
        (
            2.5,
            6.2,
            2.5,
            1.4,
            "POSA",
            "1996 • Buschmann\nLayers, Broker,\n" "Pipes & Filters, MVC",
            GRAY1,
            "P",
        ),
        (
            2.5,
            4.2,
            2.5,
            1.4,
            "GoF",
            "1994 • Gamma et al.\n23 wzorce:\n" "5 kreac. / 7 strukt. / 11 behaw.",
            GRAY2,
            "G",
        ),
        (
            5.5,
            6.2,
            2.5,
            1.4,
            "EIP",
            "2003 • Hohpe & Woolf\nMessage Channel,\n" "Router, Aggregator",
            GRAY1,
            "E",
        ),
        (
            5.5,
            4.2,
            2.5,
            1.4,
            "PoEAA",
            "2002 • M. Fowler\nRepository," " Unit of Work,\nDomain Model",
            "white",
            "P",
        ),
        (
            8.5,
            6.2,
            2.8,
            1.4,
            "Cloud\nPatterns",
            "~2015 • Azure/AWS\nCircuit Breaker,\n" "Saga, Sidecar",
            GRAY1,
            "C",
        ),
    ]

    for cx, cy, cw, ch, name, sub, fill, ml in catalogs:
        rect = FancyBboxPatch(
            (cx, cy),
            cw,
            ch,
            boxstyle="round,pad=0.1",
            lw=1.5,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            cx + cw / 2,
            cy + ch - 0.3,
            name,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
        )
        ax.text(
            cx + cw / 2,
            cy + 0.4,
            sub,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            linespacing=1.3,
        )

        # Mnemonic letter in corner
        circle = plt.Circle(
            (cx + 0.25, cy + ch - 0.25),
            0.2,
            lw=1,
            edgecolor=LN,
            facecolor=GRAY5,
        )
        ax.add_patch(circle)
        ax.text(
            cx + 0.25,
            cy + ch - 0.25,
            ml,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
        )

    # Mnemonic bar at bottom
    mnem_y = 2.2
    ax.text(
        6.0,
        mnem_y,
        "PGEP+C → Paweł Grał Efektownie Pod Chmurami",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 1.5,
        },
    )

    # Domain labels along x-axis
    domains = [
        (3.75, 1.7, "Architektura"),
        (6.75, 1.7, "Integracja / Enterprise"),
        (9.9, 1.7, "Chmura"),
    ]
    for dx, dy, dlabel in domains:
        ax.text(
            dx,
            dy,
            dlabel,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontstyle="italic",
        )

    fig.tight_layout()
    out = str(Path(OUTPUT_DIR) / "q14_catalog_map.png")
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", out)
