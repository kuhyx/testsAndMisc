"""5NF and summary flow normalization diagram functions."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_normalization_diagrams import (
    OUTPUT_DIR,
    add_arrow,
    add_label,
    create_figure,
    draw_table,
)

logger = logging.getLogger(__name__)


# ============================================================
# DIAGRAM 7: 5NF example — join dependencies
# ============================================================
def draw_5nf() -> None:
    """Draw 5nf."""
    fig, ax = create_figure(11.69, 8.5)

    # Before: ternary table
    h_before = ["Dostawca*", "Czesc*", "Projekt*"]
    r_before = [
        ["Alfa", "Sruba", "Most"],
        ["Alfa", "Sruba", "Wiezowiec"],
        ["Alfa", "Nakretka", "Most"],
        ["Beta", "Sruba", "Wiezowiec"],
        ["Beta", "Nakretka", "Wiezowiec"],
    ]
    cw_before = [0.9, 0.9, 1.0]
    draw_table(
        ax,
        0.5,
        7.8,
        "PRZED: Dostawy (klucz: Dostawca, Czesc, Projekt)",
        h_before,
        r_before,
        cw_before,
        title_fontsize=10,
    )

    add_label(ax, 3.8, 7.3, "Tabela w 4NF (brak nietrywialnych MVD),", fontsize=8)
    add_label(
        ax, 3.8, 7.0, "ale NIE w 5NF jesli zachodzi regula cykliczna:", fontsize=8
    )
    add_label(
        ax, 3.8, 6.55, "Jesli Dostawca dostarcza Czesc", fontsize=8, color="#333333"
    )
    add_label(
        ax, 3.8, 6.25, "  I Dostawca dostarcza do Projektu", fontsize=8, color="#333333"
    )
    add_label(
        ax, 3.8, 5.95, "  I Czesc jest uzywana w Projekcie", fontsize=8, color="#333333"
    )
    add_label(
        ax,
        3.8,
        5.65,
        "  ==> Dostawca dostarcza te Czesc do tego Projektu.",
        fontsize=8,
        color="black",
    )

    # Arrow down
    add_arrow(ax, 1.8, 5.1, 1.8, 4.6, "dekompozycja 5NF", "#333333")

    # After: three binary tables
    h1 = ["Dostawca*", "Czesc*"]
    r1 = [
        ["Alfa", "Sruba"],
        ["Alfa", "Nakretka"],
        ["Beta", "Sruba"],
        ["Beta", "Nakretka"],
    ]
    cw1 = [0.9, 0.9]
    draw_table(ax, 0.3, 4.3, "DostawcaCzesc", h1, r1, cw1, title_fontsize=9)

    h2 = ["Dostawca*", "Projekt*"]
    r2 = [["Alfa", "Most"], ["Alfa", "Wiezowiec"], ["Beta", "Wiezowiec"]]
    cw2 = [0.9, 1.0]
    draw_table(ax, 3.0, 4.3, "DostawcaProjekt", h2, r2, cw2, title_fontsize=9)

    h3 = ["Czesc*", "Projekt*"]
    r3 = [
        ["Sruba", "Most"],
        ["Sruba", "Wiezowiec"],
        ["Nakretka", "Most"],
        ["Nakretka", "Wiezowiec"],
    ]
    cw3 = [0.9, 1.0]
    draw_table(ax, 5.7, 4.3, "CzescProjekt", h3, r3, cw3, title_fontsize=9)

    # Join reconstruction note
    rect = mpatches.FancyBboxPatch(
        (8.3, 3.5),
        3.0,
        4.0,
        boxstyle="round,pad=0.1",
        facecolor="#F0F0F0",
        edgecolor="black",
        linewidth=1.0,
    )
    ax.add_patch(rect)

    add_label(ax, 8.5, 7.2, "5NF (PJNF):", fontsize=10)
    add_label(ax, 8.5, 6.8, "Project-Join NF", fontsize=8, color="#333333")
    add_label(ax, 8.5, 6.35, "Kazda zaleznosc", fontsize=8)
    add_label(ax, 8.5, 6.05, "zlaczenia (JD)", fontsize=8)
    add_label(ax, 8.5, 5.75, "implikowana przez", fontsize=8)
    add_label(ax, 8.5, 5.45, "klucze kandydujace.", fontsize=8)
    add_label(ax, 8.5, 4.9, "Rekonstrukcja:", fontsize=9)
    add_label(ax, 8.5, 4.55, "DC JOIN DP JOIN CP", fontsize=8, color="#333333")
    add_label(ax, 8.5, 4.2, "= oryginalna tabela", fontsize=8, color="#333333")
    add_label(ax, 8.5, 3.75, "(bezstratnie!)", fontsize=8, color="#333333")

    # Verification example at the bottom
    add_label(
        ax,
        0.3,
        2.0,
        "Weryfikacja: Alfa dostarcza Nakretke?"
        " Alfa -> Wiezowiec? Nakretka -> Wiezowiec?",
        fontsize=8,
    )
    add_label(
        ax,
        0.3,
        1.65,
        "  TAK, TAK, TAK --> wg reguly cyklicznej:"
        " Alfa dostarcza Nakretke do Wiezowca.",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        1.25,
        "Ale: Alfa dostarcza Nakretke? TAK. Alfa -> Most? TAK. Nakretka -> Most? TAK.",
        fontsize=8,
    )
    add_label(
        ax,
        0.3,
        0.9,
        "  --> Alfa dostarcza Nakretke do Mostu."
        " (Tego wiersza NIE MA w oryginale -- BLAD!)",
        fontsize=8,
        color="black",
    )
    add_label(
        ax,
        0.3,
        0.5,
        "  Dekompozycja 5NF jest poprawna TYLKO"
        " jesli regula cykliczna rzeczywiscie zachodzi!",
        fontsize=8,
        color="black",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_5nf_example.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_5nf_example.png")


# ============================================================
# DIAGRAM 8: Full normalization summary flowchart
# ============================================================
def draw_summary_flow() -> None:
    """Draw summary flow."""
    fig, ax = create_figure(11.69, 6.0)

    # Boxes for each NF
    box_y = 4.5
    box_h = 1.8
    box_w = 1.4
    gap = 0.25

    nf_data = [
        ("0NF", "Nienormalna", "Listy w\nkomorkach,\nbrak klucza"),
        ("1NF", "Atomowosc", "Kazda komorka\n= 1 wartosc,\njest klucz"),
        ("2NF", "Pelny klucz", "Brak czesciowej\nzaleznosci od\nklucza zlozonego"),
        ("3NF", "Tylko klucz", "Brak zaleznosci\nprzechodniej\nA->B->C"),
        ("BCNF", "Nadklucz", "Lewa strona\nkazdej FD\n= nadklucz"),
        ("4NF", "Brak MVD", "Brak nietryw.\nwielowart.\nzaleznosci"),
        ("5NF", "Brak JD", "Kazda zal.\nzlaczenia\nimpl. kluczem"),
    ]

    for i, (name, subtitle, desc) in enumerate(nf_data):
        x = 0.3 + i * (box_w + gap)

        # Main box
        rect = mpatches.FancyBboxPatch(
            (x, box_y - box_h),
            box_w,
            box_h,
            boxstyle="round,pad=0.05",
            facecolor="#F5F5F5" if i == 0 else "#FFFFFF",
            edgecolor="black",
            linewidth=1.2,
        )
        ax.add_patch(rect)

        # NF name
        ax.text(
            x + box_w / 2,
            box_y - 0.15,
            name,
            fontsize=12,
            fontweight="bold",
            ha="center",
            va="top",
            family="monospace",
        )

        # Subtitle
        ax.text(
            x + box_w / 2,
            box_y - 0.45,
            subtitle,
            fontsize=7,
            ha="center",
            va="top",
            family="monospace",
            color="#333333",
        )

        # Description
        ax.text(
            x + box_w / 2,
            box_y - 0.75,
            desc,
            fontsize=6.5,
            ha="center",
            va="top",
            family="monospace",
            color="#555555",
            linespacing=1.3,
        )

        # Arrow to next
        if i < len(nf_data) - 1:
            ax.annotate(
                "",
                xy=(x + box_w + 0.02, box_y - box_h / 2),
                xytext=(x + box_w + gap - 0.02, box_y - box_h / 2),
                arrowprops={"arrowstyle": "<-", "color": "black", "lw": 1.5},
            )

    # Mnemonic quote at the bottom
    ax.text(
        5.85,
        2.2,
        '"Klucz, caly klucz i tylko klucz -- tak mi dopomoz Codd"',
        fontsize=11,
        ha="center",
        va="center",
        family="monospace",
        style="italic",
    )
    ax.text(
        5.85,
        1.8,
        "1NF: klucz istnieje  |  2NF: caly klucz  |  3NF: tylko klucz",
        fontsize=9,
        ha="center",
        va="center",
        family="monospace",
        color="#333333",
    )
    ax.text(
        5.85,
        1.4,
        "BCNF: kazdy determinant = nadklucz  |  4NF: +brak MVD  |  5NF: +brak JD",
        fontsize=9,
        ha="center",
        va="center",
        family="monospace",
        color="#333333",
    )

    # Hierarchy
    ax.text(
        5.85,
        0.8,
        "5NF  (zawiera sie w)  4NF  (zaw.)  BCNF"
        "  (zaw.)  3NF  (zaw.)  2NF  (zaw.)  1NF",
        fontsize=8,
        ha="center",
        va="center",
        family="monospace",
        color="#555555",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_summary_flow.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_summary_flow.png")
