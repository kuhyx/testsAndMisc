"""Q9 diagrams 14-16: classic sync problems, mechanism comparison, semaphore."""

from __future__ import annotations

from _q9_common import (
    FS,
    FS_LABEL,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OCCUPIED_SLOTS,
    draw_arrow,
    draw_box,
    draw_table,
    save_fig,
)
import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# 14. Bounded buffer + readers-writers + philosophers
# ============================================================
def _draw_bounded_buffer_panel(ax: plt.Axes) -> None:
    """Draw the bounded-buffer (producer-consumer) panel."""
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Producent-Konsument\n(Bounded Buffer, N=4)", fontsize=FS, fontweight="bold"
    )

    draw_box(
        ax,
        0.2,
        4.0,
        2.0,
        1.2,
        "Producent\nP(empty)\nP(mutex)\nwstaw()\nV(mutex)\nV(full)",
        fill=GRAY1,
        fontsize=5.5,
    )
    items = ["A", "B", "", ""]
    for i, item in enumerate(items):
        x = 2.8 + i * 0.9
        fill = GRAY3 if item else "white"
        draw_box(
            ax,
            x,
            4.3,
            0.9,
            0.7,
            item,
            fill=fill,
            fontsize=FS,
            fontweight="bold",
            rounded=False,
        )
    ax.text(4.6, 5.2, "Bufor (N=4)", fontsize=FS_SMALL, ha="center", fontweight="bold")
    draw_box(
        ax,
        6.0,
        4.0,
        2.0,
        1.2,
        "Konsument\nP(full)\nP(mutex)\npobierz()\nV(mutex)\nV(empty)",
        fill=GRAY4,
        fontsize=5.5,
    )
    draw_arrow(ax, 2.2, 4.6, 2.8, 4.65, lw=1.2)
    draw_arrow(ax, 6.4, 4.65, 6.0, 4.6, lw=1.2)

    sems = [("mutex = 1", GRAY2), ("empty = N", GRAY1), ("full = 0", GRAY3)]
    for i, (s, c) in enumerate(sems):
        draw_box(
            ax,
            2.0,
            2.5 - i * 0.6,
            4.0,
            0.45,
            s,
            fill=c,
            fontsize=FS_SMALL,
            fontweight="bold",
        )

    ax.text(
        4.0,
        0.5,
        "KOLEJNOŚĆ: P(empty/full)\nPRZED P(mutex)!\nOdwrotnie = DEADLOCK",
        fontsize=5.5,
        ha="center",
        fontweight="bold",
        color="#C62828",
        bbox={"boxstyle": "round", "facecolor": "#F8D7DA", "edgecolor": "#C62828"},
    )


def _draw_readers_writers_panel(ax: plt.Axes) -> None:
    """Draw the readers-writers panel."""
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Czytelnicy-Pisarze\n(Readers-Writers)", fontsize=FS, fontweight="bold"
    )

    draw_box(
        ax,
        2.5,
        3.5,
        3.0,
        1.5,
        "Dane\n(współdzielone)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    for i in range(3):
        x = 0.3 + i * 1.0
        draw_box(
            ax,
            x,
            5.5,
            0.8,
            0.7,
            f"R{i + 1}",
            fill=GRAY4,
            fontsize=FS,
            fontweight="bold",
        )
        draw_arrow(ax, x + 0.4, 5.5, 3.0 + i * 0.5, 5.0, lw=1)

    ax.text(
        1.5,
        6.5,
        "Czytelnicy (wielu naraz)",
        fontsize=FS_SMALL,
        ha="center",
        fontweight="bold",
    )

    draw_box(
        ax, 5.5, 5.5, 1.5, 0.7, "Pisarz", fill=GRAY5, fontsize=FS, fontweight="bold"
    )
    draw_arrow(ax, 6.25, 5.5, 5.0, 5.0, lw=1.5)
    ax.text(
        6.25,
        6.5,
        "WYŁĄCZNY",
        fontsize=FS_SMALL,
        ha="center",
        fontweight="bold",
        color="#C62828",
    )

    rules = [
        "Wielu czytelników = OK",
        "Jeden pisarz = wyłączny",
        "Czytelnik + Pisarz = ✗",
        "Problem: pisarze głodują",
    ]
    for i, r in enumerate(rules):
        ax.text(4.0, 2.5 - i * 0.45, r, fontsize=FS_SMALL, ha="center")

    ax.text(
        4.0,
        0.5,
        "Rozwiązanie:\nrw_mutex + count_mutex\n+ zmienna readers",
        fontsize=5.5,
        ha="center",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )


def _draw_philosophers_panel(ax: plt.Axes) -> None:
    """Draw the dining-philosophers panel."""
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Ucztujący filozofowie\n(Dining Philosophers)", fontsize=FS, fontweight="bold"
    )

    cx, cy, r = 4.0, 3.8, 1.8
    table = plt.Circle((cx, cy), 0.8, fill=True, facecolor=GRAY2, edgecolor=LN, lw=1.5)
    ax.add_patch(table)
    ax.text(cx, cy, "Stół", fontsize=FS, ha="center", fontweight="bold")

    for i in range(5):
        angle = np.pi / 2 + i * 2 * np.pi / 5
        px = cx + r * np.cos(angle)
        py = cy + r * np.sin(angle)
        circle = plt.Circle(
            (px, py), 0.35, fill=True, facecolor=GRAY1, edgecolor=LN, lw=1.2
        )
        ax.add_patch(circle)
        ax.text(
            px, py, f"F{i}", ha="center", va="center", fontsize=FS, fontweight="bold"
        )

        fork_angle = np.pi / 2 + (i + 0.5) * 2 * np.pi / 5
        fx = cx + (r * 0.6) * np.cos(fork_angle)
        fy = cy + (r * 0.6) * np.sin(fork_angle)
        ax.plot(
            [fx - 0.1, fx + 0.1],
            [fy - 0.15, fy + 0.15],
            color=LN,
            lw=2.5,
            solid_capstyle="round",
        )
        ax.text(fx + 0.2, fy + 0.15, f"w{i}", fontsize=5, color="#555555")

    rules = [
        "Jedzenie = 2 widelce",
        "Naiwne → DEADLOCK",
        "Fix: F4 bierze odwrotnie",
        "Alt: semafor(4)",
    ]
    for i, r in enumerate(rules):
        ax.text(4.0, 1.2 - i * 0.35, r, fontsize=FS_SMALL, ha="center")


def gen_classic_problems() -> None:
    """Gen classic problems."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 5))
    fig.suptitle(
        "Klasyczne problemy synchronizacji", fontsize=FS_TITLE, fontweight="bold"
    )

    _draw_bounded_buffer_panel(axes[0])
    _draw_readers_writers_panel(axes[1])
    _draw_philosophers_panel(axes[2])

    fig.tight_layout(rect=[0, 0, 1, 0.88])
    save_fig(fig, "q9_classic_problems.png")


# ============================================================
# 15. Sync mechanisms comparison + mutex/sem/spinlock
# ============================================================
def gen_sync_comparison() -> None:
    """Gen sync comparison."""
    fig, axes = plt.subplots(2, 1, figsize=(9, 7))

    # Top: comparison table
    ax = axes[0]
    ax.set_xlim(0, 11.5)
    ax.set_ylim(-5, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Mechanizmy synchronizacji — porównanie",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    headers = ["Mechanizm", "Opis", "Kiedy używać"]
    col_w = [2.5, 4.5, 4.0]
    rows = [
        ["Mutex", "Zamek: 1 wątek w sekcji", "Sekcja krytyczna"],
        ["Semafor(n)", "Licznik: max n wątków", "Ograniczone zasoby (n miejsc)"],
        ["Monitor", "Obiekt z wbudowanym mutex", "Java synchronized"],
        ["Cond. Variable", "wait()/signal() na warunek", "Producent-konsument"],
        ["Spinlock", "Aktywne czekanie (busy-wait)", "Bardzo krótkie sekcje (<1 μs)"],
        ["RW Lock", "Wielu czytelników LUB 1 pisarz", "Bazy danych, cache"],
        ["Barrier", "Czekaj aż wszyscy dotrą", "Obliczenia równoległe"],
    ]
    draw_table(
        ax, headers, rows, x0=0.25, y0=0.5, col_widths=col_w, row_h=0.5, fontsize=7
    )

    # Bottom: mutex vs semafor vs spinlock
    ax = axes[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Mutex vs Semafor vs Spinlock", fontsize=FS_TITLE, fontweight="bold", pad=5
    )

    # Mutex
    draw_box(ax, 0.3, 2.5, 3.5, 2.0, "", fill=GRAY4)
    ax.text(2.05, 4.2, "MUTEX", fontsize=FS_LABEL, fontweight="bold", ha="center")
    ax.text(2.05, 3.6, "= klucz do łazienki\n(1 osoba)", fontsize=FS, ha="center")
    ax.text(
        2.05,
        2.8,
        "Wątek ZASYPIA gdy czeka\nOS go obudzi (~μs)",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
    )

    # Semafor
    draw_box(ax, 4.3, 2.5, 3.5, 2.0, "", fill=GRAY1)
    ax.text(6.05, 4.2, "SEMAFOR(n)", fontsize=FS_LABEL, fontweight="bold", ha="center")
    ax.text(
        6.05, 3.6, "= parking na n miejsc\n(n wątków naraz)", fontsize=FS, ha="center"
    )
    ax.text(
        6.05,
        2.8,
        "Semafor(1) = mutex\nP() = zmniejsz, V() = zwiększ",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
    )

    # Spinlock
    draw_box(ax, 8.3, 2.5, 3.5, 2.0, "", fill=GRAY2)
    ax.text(10.05, 4.2, "SPINLOCK", fontsize=FS_LABEL, fontweight="bold", ha="center")
    ax.text(
        10.05, 3.6, "= obrotowe drzwi\n(kręcisz się w kółko)", fontsize=FS, ha="center"
    )
    ax.text(
        10.05,
        2.8,
        "Wątek KRĘCI się w pętli\nLepszy gdy sekcja < 1 μs",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
    )

    # Dividing rule
    ax.text(
        6.0,
        1.5,
        "Reguła kciuka:  sekcja > 1 μs → MUTEX  |  "
        "sekcja < 1 μs → SPINLOCK  |  n jednocześnie → SEMAFOR(n)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    fig.tight_layout()
    save_fig(fig, "q9_sync_comparison.png")


# ============================================================
# 16. Semaphore concept diagram
# ============================================================
def gen_semaphore_concept() -> None:
    """Gen semaphore concept."""
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Semafor — koncepcja (parking na 3 miejsca)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Parking slots
    for i in range(3):
        x = 2.0 + i * 2.0
        occupied = i < OCCUPIED_SLOTS
        fill = GRAY3 if occupied else "white"
        label = f"Wątek {i + 1}" if occupied else "(wolne)"
        draw_box(
            ax,
            x,
            2.5,
            1.5,
            1.2,
            label,
            fill=fill,
            fontsize=FS,
            fontweight="bold" if occupied else "normal",
            rounded=False,
        )

    ax.text(
        5.0,
        4.2,
        "semafor(3): counter = 1 (jedno wolne miejsce)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )

    # Waiting thread
    draw_box(
        ax,
        0.2,
        0.5,
        1.5,
        0.8,
        "Wątek 4\nP() → czeka",
        fill="#F8D7DA",
        fontsize=FS_SMALL,
    )
    draw_arrow(ax, 1.7, 0.9, 2.0, 2.5, lw=1.2, color="#C62828")

    ax.text(
        5.0,
        0.6,
        "P() = counter--  (jeśli 0 → czekaj)\nV() = counter++  (obudź czekającego)",
        fontsize=FS,
        ha="center",
        family="monospace",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    save_fig(fig, "q9_semaphore_concept.png")
