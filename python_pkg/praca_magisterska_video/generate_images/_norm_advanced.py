"""3NF, BCNF, 4NF normalization diagram functions."""

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
# DIAGRAM 4: 3NF — no transitive dependencies
# ============================================================
def draw_3nf() -> None:
    """Draw 3nf."""
    fig, ax = create_figure(11.69, 6.5)

    # Student table after removing transitive dependency
    h1 = ["StID*", "Imie", "WydzialID"]
    r1 = [["1", "Anna", "W4"], ["2", "Jan", "W4"], ["3", "Ewa", "W2"]]
    cw1 = [0.55, 0.55, 0.85]
    draw_table(ax, 0.3, 5.8, "Studenci (kl: StID)", h1, r1, cw1, title_fontsize=9)

    # Wydzialy (new!)
    h2 = ["WydzialID*", "NazwaWydzialu"]
    r2 = [["W4", "EiTI"], ["W2", "Fizyka"]]
    cw2 = [0.85, 1.2]
    draw_table(ax, 2.6, 5.8, "Wydzialy (kl: WydzialID)", h2, r2, cw2, title_fontsize=9)

    # Kursy
    h3 = ["KursID*", "NazwaKursu"]
    r3 = [["K10", "Bazy danych"], ["K20", "Algorytmy"], ["K30", "Optyka"]]
    cw3 = [0.7, 1.1]
    draw_table(ax, 5.2, 5.8, "Kursy (kl: KursID)", h3, r3, cw3, title_fontsize=9)

    # Zapisy (highlight BCNF violation)
    h4 = ["StID*", "KursID*", "Prowadzacy"]
    r4 = [
        ["1", "K10", "Kowalski"],
        ["1", "K20", "Nowak"],
        ["2", "K10", "Kowalski"],
        ["3", "K30", "Wisniewski"],
    ]
    cw4 = [0.55, 0.7, 1.05]
    draw_table(
        ax,
        7.8,
        5.8,
        "Zapisy (kl: StID, KursID)",
        h4,
        r4,
        cw4,
        highlight_cols={1, 2},
        title_fontsize=9,
    )

    # Annotations
    add_label(
        ax,
        0.3,
        3.3,
        "KROK: Rozdzielono Studenci -> Studenci + Wydzialy (usun. zal. przechodnia).",
        fontsize=9,
    )
    add_label(
        ax,
        0.3,
        2.95,
        "  StID -> WydzialID -> NazwaWydzialu"
        "  rozbito: NazwaWydzialu w osobnej tabeli.",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        2.55,
        'PROBLEM BCNF w "Zapisy":  FD: Prowadzacy -> KursID (1 prowadzacy = 1 kurs)',
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.3,
        2.2,
        "  Prowadzacy NIE jest nadkluczem tabeli Zapisy -> NARUSZENIE BCNF.",
        fontsize=9,
        color="black",
    )
    add_label(
        ax,
        0.3,
        1.85,
        "  3NF OK, bo KursID jest atrybutem pierwszym (prime) -> wyjatek 3NF.",
        fontsize=9,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        1.5,
        "  BCNF nie ma takiego wyjatku"
        " -> kazda nietrywialna FD wymaga nadklucza po lewej.",
        fontsize=9,
        color="#333333",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_3nf_tables.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_3nf_tables.png")


# ============================================================
# DIAGRAM 5: BCNF — every determinant is a superkey
# ============================================================
def draw_bcnf() -> None:
    """Draw bcnf."""
    fig, ax = create_figure(11.69, 7.5)

    # Studenci
    h1 = ["StID*", "Imie", "WydzialID"]
    r1 = [["1", "Anna", "W4"], ["2", "Jan", "W4"], ["3", "Ewa", "W2"]]
    cw1 = [0.55, 0.55, 0.85]
    draw_table(ax, 0.3, 6.8, "Studenci", h1, r1, cw1, title_fontsize=9)

    # Wydzialy
    h2 = ["WydzialID*", "NazwaWydz."]
    r2 = [["W4", "EiTI"], ["W2", "Fizyka"]]
    cw2 = [0.85, 1.0]
    draw_table(ax, 2.5, 6.8, "Wydzialy", h2, r2, cw2, title_fontsize=9)

    # Kursy
    h3 = ["KursID*", "NazwaKursu"]
    r3 = [["K10", "Bazy danych"], ["K20", "Algorytmy"], ["K30", "Optyka"]]
    cw3 = [0.7, 1.1]
    draw_table(ax, 4.8, 6.8, "Kursy", h3, r3, cw3, title_fontsize=9)

    # ProwadzacyKurs (NEW - from BCNF decomposition)
    h4 = ["Prowadzacy*", "KursID"]
    r4 = [["Kowalski", "K10"], ["Nowak", "K20"], ["Wisniewski", "K30"]]
    cw4 = [1.05, 0.7]
    draw_table(
        ax, 7.2, 6.8, "ProwadzacyKurs (kl: Prow.)", h4, r4, cw4, title_fontsize=9
    )

    # New student-advisor junction table
    h5 = ["StID*", "Prowadzacy*"]
    r5 = [["1", "Kowalski"], ["1", "Nowak"], ["2", "Kowalski"], ["3", "Wisniewski"]]
    cw5 = [0.55, 1.05]
    draw_table(ax, 9.5, 6.8, "StudentProw. (kl: oba)", h5, r5, cw5, title_fontsize=9)

    # Telefony
    h6 = ["StID*", "Telefon*"]
    r6 = [["1", "111-222"], ["1", "333-444"], ["2", "555-666"], ["3", "777-888"]]
    cw6 = [0.55, 0.85]
    draw_table(ax, 0.3, 4.6, "Telefony", h6, r6, cw6, title_fontsize=9)

    # Annotations
    add_label(
        ax, 0.3, 2.9, "KROK: Zapisy(StID, KursID, Prowadzacy) rozbite na:", fontsize=9
    )
    add_label(
        ax,
        0.3,
        2.55,
        "  ProwadzacyKurs(Prowadzacy, KursID)"
        "  — FD: Prowadzacy -> KursID, klucz: Prowadzacy",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        2.25,
        "  StudentProwadzacy(StID, Prowadzacy)  — ktory student u ktorego prowadzacego",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        0.3,
        1.85,
        "Teraz KAZDA nietrywialna FD ma nadklucz po lewej stronie -> BCNF spelnione.",
        fontsize=9,
    )
    add_label(
        ax,
        0.3,
        1.45,
        "Rekonstrukcja: StudentProw. JOIN ProwadzacyKurs"
        " ON Prowadzacy -> odtworzenie Zapisy.",
        fontsize=8,
        color="#333333",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_bcnf_tables.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_bcnf_tables.png")


# ============================================================
# DIAGRAM 6: 4NF example — multi-valued dependencies
# ============================================================
def draw_4nf() -> None:
    """Draw 4nf."""
    fig, ax = create_figure(11.69, 7.5)

    # Before: table with MVD violation
    h_before = ["StID*", "Hobby*", "Umiejetnosc*"]
    r_before = [
        ["1", "Szachy", "Python"],
        ["1", "Szachy", "SQL"],
        ["1", "Bieganie", "Python"],
        ["1", "Bieganie", "SQL"],
        ["2", "Plywanie", "Java"],
    ]
    cw_before = [0.55, 0.9, 1.0]
    draw_table(
        ax,
        0.5,
        6.8,
        "PRZED: StudentAktywnosci (klucz: StID, Hobby, Umiejetnosc)",
        h_before,
        r_before,
        cw_before,
        highlight_cols={1, 2},
        title_fontsize=10,
    )

    # Arrows
    add_label(ax, 3.5, 6.3, "StID  ->>  Hobby", fontsize=9, color="black")
    add_label(ax, 3.5, 6.0, "StID  ->>  Umiejetnosc", fontsize=9, color="black")
    add_label(ax, 3.5, 5.6, "NIEZALEZNE MVD w jednej tabeli", fontsize=9, color="black")
    add_label(
        ax,
        3.5,
        5.2,
        "= iloczyn kartezjanski = NARUSZENIE 4NF",
        fontsize=9,
        color="black",
    )

    # After: two tables
    add_arrow(ax, 3.0, 4.2, 3.0, 3.7, "", "#333333")
    add_label(ax, 3.2, 3.95, "dekompozycja", fontsize=8, color="#333333")

    h_hobby = ["StID*", "Hobby*"]
    r_hobby = [["1", "Szachy"], ["1", "Bieganie"], ["2", "Plywanie"]]
    cw_hobby = [0.55, 0.9]
    draw_table(
        ax, 0.5, 3.5, "PO: StudentHobby", h_hobby, r_hobby, cw_hobby, title_fontsize=10
    )

    h_skill = ["StID*", "Umiejetnosc*"]
    r_skill = [["1", "Python"], ["1", "SQL"], ["2", "Java"]]
    cw_skill = [0.55, 1.0]
    draw_table(
        ax,
        3.5,
        3.5,
        "PO: StudentUmiejetnosc",
        h_skill,
        r_skill,
        cw_skill,
        title_fontsize=10,
    )

    # Summary on the right side
    add_label(ax, 6.5, 6.5, "4NF: BCNF + brak nietrywialnych MVD", fontsize=10)
    add_label(
        ax, 6.5, 6.1, "MVD X ->> Y: jeden X = ZBIOR Y-ow,", fontsize=8, color="#333333"
    )
    add_label(
        ax, 6.5, 5.8, "niezaleznie od reszty kolumn.", fontsize=8, color="#333333"
    )
    add_label(
        ax, 6.5, 5.35, "Naruszenie: Student 1 ma 2 hobby i 2 umiejetnosci", fontsize=8
    )
    add_label(
        ax, 6.5, 5.05, "  -> 2 x 2 = 4 wiersze (iloczyn kartezjanski!)", fontsize=8
    )
    add_label(
        ax, 6.5, 4.65, "Naprawa: rozdziel niezalezne MVD do osobnych tabel.", fontsize=8
    )
    add_label(
        ax,
        6.5,
        4.25,
        "Po dekompozycji: 3 + 3 = 6 wierszy zamiast 5 z ilocz.",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax, 6.5, 3.85, "  (ale BEZ sztucznych kombinacji!)", fontsize=8, color="#333333"
    )

    # Key insight box
    rect = mpatches.FancyBboxPatch(
        (6.3, 2.5),
        5.0,
        1.0,
        boxstyle="round,pad=0.1",
        facecolor="#F0F0F0",
        edgecolor="black",
        linewidth=1.0,
    )
    ax.add_patch(rect)
    add_label(ax, 6.5, 3.2, "ROZNICA 4NF vs BCNF:", fontsize=9)
    add_label(
        ax,
        6.5,
        2.85,
        "BCNF dotyczy FD (X -> Y, jedna wartosc)",
        fontsize=8,
        color="#333333",
    )
    add_label(
        ax,
        6.5,
        2.55,
        "4NF dotyczy MVD (X ->> Y, zbior wartosci)",
        fontsize=8,
        color="#333333",
    )

    fig.savefig(
        str(Path(OUTPUT_DIR) / "nf_4nf_example.png"),
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.2,
    )
    plt.close(fig)
    logger.info("Generated: nf_4nf_example.png")
