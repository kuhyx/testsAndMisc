"""0NF, 1NF, 2NF normalization diagram functions."""

from __future__ import annotations

import logging
from pathlib import Path

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
# DIAGRAM 1: 0NF Table
# ============================================================
def draw_0nf() -> None:
    """Draw 0nf."""
    fig, ax = create_figure(11.69, 5.5)

    headers = [
        "StID",
        "Imie",
        "Telefony",
        "KursID",
        "NazwaKursu",
        "Prowadzacy",
        "WydzialID",
        "NazwaWydzialu",
    ]
    rows = [
        [
            "1",
            "Anna",
            "111-222, 333-444",
            "K10",
            "Bazy danych",
            "Kowalski",
            "W4",
            "EiTI",
        ],
        ["1", "Anna", "111-222, 333-444", "K20", "Algorytmy", "Nowak", "W4", "EiTI"],
        ["2", "Jan", "555-666", "K10", "Bazy danych", "Kowalski", "W4", "EiTI"],
        ["3", "Ewa", "777-888", "K30", "Optyka", "Wisniewski", "W2", "Fizyka"],
    ]
    col_widths = [0.5, 0.55, 1.55, 0.65, 1.1, 1.05, 0.85, 1.2]

    # Highlight the non-atomic column
    draw_table(
        ax,
        0.8,
        4.5,
        "0NF: Rejestr (forma nienormalna)",
        headers,
        rows,
        col_widths,
        highlight_cols={2},  # Telefony column
        title_fontsize=11,
    )

    # Annotations
    add_label(
        ax,
        0.8,
        1.9,
        'PROBLEM: Kolumna "Telefony" zawiera LISTY wartosci (nieatomowe).',
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.8,
        1.55,
        'Redundancja: "Anna", "W4", "EiTI", "Bazy danych" powtorzone wielokrotnie.',
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.8,
        1.2,
        (
            "Zaleznosci funkcyjne:  StID -> Imie, WydzialID"
            "    |    WydzialID -> NazwaWydzialu"
        ),
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.8,
        0.9,
        (
            "  KursID -> NazwaKursu    |    (StID,KursID)"
            " -> Prowadzacy    |    Prowadzacy -> KursID"
        ),
        fontsize=8,
        color="#333333",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_0nf_table.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_0nf_table.png")


# ============================================================
# DIAGRAM 2: 1NF — atomic values
# ============================================================
def draw_1nf() -> None:
    """Draw 1nf."""
    fig, ax = create_figure(11.69, 6.0)

    # Main table after removing Telefony
    headers1 = [
        "StID*",
        "Imie",
        "KursID*",
        "NazwaKursu",
        "Prowadzacy",
        "WydzialID",
        "NazwaWydzialu",
    ]
    rows1 = [
        ["1", "Anna", "K10", "Bazy danych", "Kowalski", "W4", "EiTI"],
        ["1", "Anna", "K20", "Algorytmy", "Nowak", "W4", "EiTI"],
        ["2", "Jan", "K10", "Bazy danych", "Kowalski", "W4", "EiTI"],
        ["3", "Ewa", "K30", "Optyka", "Wisniewski", "W2", "Fizyka"],
    ]
    cw1 = [0.55, 0.55, 0.7, 1.1, 1.05, 0.85, 1.2]

    draw_table(
        ax,
        0.5,
        5.2,
        "1NF: Rejestr  (klucz: StID, KursID)",
        headers1,
        rows1,
        cw1,
        title_fontsize=10,
    )

    # Telefony table
    headers2 = ["StID*", "Telefon*"]
    rows2 = [
        ["1", "111-222"],
        ["1", "333-444"],
        ["2", "555-666"],
        ["3", "777-888"],
    ]
    cw2 = [0.55, 0.85]

    draw_table(
        ax,
        7.5,
        5.2,
        "Telefony  (klucz: StID, Telefon)",
        headers2,
        rows2,
        cw2,
        title_fontsize=10,
    )

    # Arrow
    add_arrow(ax, 6.6, 4.3, 7.4, 4.3, "wydzielono", "#333333")

    # Annotations
    add_label(
        ax,
        0.5,
        2.6,
        'KROK: Nieatomowa kolumna "Telefony" wydzielona do osobnej tabeli.',
        fontsize=9,
    )
    add_label(
        ax,
        0.5,
        2.25,
        "Kazda komorka zawiera JEDNA wartosc. Klucz glowny wyznaczony.",
        fontsize=9,
    )
    add_label(
        ax,
        0.5,
        1.85,
        "PROBLEM 2NF: NazwaKursu zalezy TYLKO od KursID (czesc klucza).",
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.5,
        1.5,
        (
            "             Imie, WydzialID, NazwaWydzialu"
            " zaleza TYLKO od StID (czesc klucza)."
        ),
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.5,
        1.15,
        "  --> Czesciowe zaleznosci od klucza zlozonego = NARUSZENIE 2NF.",
        fontsize=9,
        color="black",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_1nf_tables.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_1nf_tables.png")


# ============================================================
# DIAGRAM 3: 2NF — no partial dependencies
# ============================================================
def draw_2nf() -> None:
    """Draw 2nf."""
    fig, ax = create_figure(11.69, 6.5)

    # Studenci
    h1 = ["StID*", "Imie", "WydzialID", "NazwaWydzialu"]
    r1 = [
        ["1", "Anna", "W4", "EiTI"],
        ["2", "Jan", "W4", "EiTI"],
        ["3", "Ewa", "W2", "Fizyka"],
    ]
    cw1 = [0.55, 0.55, 0.85, 1.2]
    draw_table(
        ax,
        0.3,
        5.8,
        "Studenci (kl: StID)",
        h1,
        r1,
        cw1,
        highlight_cols={2, 3},
        title_fontsize=9,
    )

    # Kursy
    h2 = ["KursID*", "NazwaKursu"]
    r2 = [["K10", "Bazy danych"], ["K20", "Algorytmy"], ["K30", "Optyka"]]
    cw2 = [0.7, 1.1]
    draw_table(ax, 4.0, 5.8, "Kursy (kl: KursID)", h2, r2, cw2, title_fontsize=9)

    # Zapisy
    h3 = ["StID*", "KursID*", "Prowadzacy"]
    r3 = [
        ["1", "K10", "Kowalski"],
        ["1", "K20", "Nowak"],
        ["2", "K10", "Kowalski"],
        ["3", "K30", "Wisniewski"],
    ]
    cw3 = [0.55, 0.7, 1.05]
    draw_table(ax, 6.8, 5.8, "Zapisy (kl: StID, KursID)", h3, r3, cw3, title_fontsize=9)

    # Telefony
    h4 = ["StID*", "Telefon*"]
    r4 = [["1", "111-222"], ["1", "333-444"], ["2", "555-666"], ["3", "777-888"]]
    cw4 = [0.55, 0.85]
    draw_table(ax, 9.5, 5.8, "Telefony", h4, r4, cw4, title_fontsize=9)

    # Annotations
    add_label(
        ax,
        0.3,
        3.3,
        (
            "KROK: Rozbito czesc. zaleznosci"
            " — atrybuty zalezne od czesci klucza wydzielone."
        ),
        fontsize=9,
    )
    add_label(
        ax,
        0.3,
        2.95,
        "  StID -> Imie, WydzialID, NazwaWydzialu  ==>  tabela Studenci",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        2.65,
        "  KursID -> NazwaKursu                    ==>  tabela Kursy",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        2.3,
        'PROBLEM 3NF w "Studenci": StID -> WydzialID -> NazwaWydzialu',
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.3,
        1.95,
        "  NazwaWydzialu zalezy od WydzialID (nie-klucz), nie bezposrednio od StID.",
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.3,
        1.6,
        "  --> Zaleznosc PRZECHODNIA = NARUSZENIE 3NF.",
        fontsize=9,
        color="black",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_2nf_tables.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_2nf_tables.png")
