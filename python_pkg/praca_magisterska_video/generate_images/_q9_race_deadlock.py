"""Q9 diagrams 10-13: race conditions, deadlock, Coffman, starvation."""

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
    draw_arrow,
    draw_box,
    draw_table,
    save_fig,
)
import matplotlib.pyplot as plt


# ============================================================
# 10. Race condition (simple x + bank timeline)
# ============================================================
def gen_race_condition() -> None:
    """Gen race condition."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    fig.suptitle(
        "Wyścig (Race Condition) — przykłady", fontsize=FS_TITLE, fontweight="bold"
    )

    # Panel 1: simple x increment
    ax = axes[0]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Prosty wyścig: x = x + 1", fontsize=FS_LABEL, fontweight="bold")

    # Timeline
    steps_a = ["czytaj x (=0)", "dodaj 1", "zapisz x (=1)"]
    steps_b = ["czytaj x (=0)", "dodaj 1", "zapisz x (=1)"]
    ax.text(2.0, 6.3, "Wątek A", fontsize=FS_LABEL, ha="center", fontweight="bold")
    ax.text(6.0, 6.3, "Wątek B", fontsize=FS_LABEL, ha="center", fontweight="bold")
    ax.plot([2, 2], [0.8, 6.0], color=LN, lw=1)
    ax.plot([6, 6], [0.8, 6.0], color=LN, lw=1)

    for i, (sa, sb) in enumerate(zip(steps_a, steps_b, strict=False)):
        y = 5.3 - i * 1.2
        draw_box(ax, 0.5, y, 3.0, 0.6, sa, fill=GRAY4, fontsize=FS)
        draw_box(ax, 4.5, y - 0.3, 3.0, 0.6, sb, fill=GRAY1, fontsize=FS)

    ax.text(
        4.0,
        0.4,
        "Wynik: x = 1  (powinno 2!)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color="#C62828",
        bbox={"boxstyle": "round", "facecolor": "#F8D7DA", "edgecolor": "#C62828"},
    )

    # Panel 2: bank account
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Konto bankowe: saldo = 1000 zł", fontsize=FS_LABEL, fontweight="bold")

    ax.text(2.5, 6.3, "Wątek A (+500)", fontsize=FS, ha="center", fontweight="bold")
    ax.text(7.5, 6.3, "Wątek B (-200)", fontsize=FS, ha="center", fontweight="bold")
    ax.plot([2.5, 2.5], [0.8, 6.0], color=LN, lw=1)
    ax.plot([7.5, 7.5], [0.8, 6.0], color=LN, lw=1)

    events = [
        ("t1", "czytaj → 1000", "", 5.3),
        ("t2", "", "czytaj → 1000", 4.6),
        ("t3", "1000+500=1500", "", 3.9),
        ("t4", "", "1000-200=800", 3.2),
        ("t5", "zapisz 1500", "", 2.5),
        ("t6", "", "zapisz 800 ✗", 1.8),
    ]
    for t, a, b, y in events:
        ax.text(0.3, y + 0.15, t, fontsize=FS_SMALL, fontweight="bold", va="center")
        if a:
            draw_box(ax, 1.0, y, 3.0, 0.45, a, fill=GRAY4, fontsize=FS_SMALL)
        if b:
            fill = "#F8D7DA" if "✗" in b else GRAY1
            draw_box(ax, 6.0, y, 3.0, 0.45, b, fill=fill, fontsize=FS_SMALL)

    ax.text(
        5.0,
        0.4,
        "Wynik: 800 zł  (powinno 1300!)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color="#C62828",
        bbox={"boxstyle": "round", "facecolor": "#F8D7DA", "edgecolor": "#C62828"},
    )

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save_fig(fig, "q9_race_condition.png")


# ============================================================
# 11. Deadlock scenario + cycle
# ============================================================
def gen_deadlock_scenario() -> None:
    """Gen deadlock scenario."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Zakleszczenie (Deadlock)", fontsize=FS_TITLE, fontweight="bold")

    # Panel 1: timeline
    ax = axes[0]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Scenariusz z 2 mutexami", fontsize=FS_LABEL, fontweight="bold")

    ax.text(2.5, 5.3, "Wątek A", fontsize=FS_LABEL, ha="center", fontweight="bold")
    ax.text(6.0, 5.3, "Wątek B", fontsize=FS_LABEL, ha="center", fontweight="bold")

    steps = [
        ("lock(mutex1) OK", "", "trzyma", False, 4.5),
        ("", "lock(mutex2) OK", "trzyma", False, 3.7),
        ("lock(mutex2) ...WAIT", "", "CZEKA!", True, 2.9),
        ("", "lock(mutex1) ...WAIT", "CZEKA!", True, 2.1),
    ]
    for a_text, b_text, _note, is_wait, y in steps:
        if a_text:
            fill = "#F8D7DA" if is_wait else GRAY4
            draw_box(ax, 0.5, y, 3.3, 0.55, a_text, fill=fill, fontsize=FS_SMALL)
        if b_text:
            fill = "#F8D7DA" if is_wait else GRAY4
            draw_box(ax, 4.3, y, 3.3, 0.55, b_text, fill=fill, fontsize=FS_SMALL)

    ax.text(
        4.0,
        1.2,
        "DEADLOCK!\nŻaden nie odpuści",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color="#C62828",
        bbox={"boxstyle": "round", "facecolor": "#F8D7DA", "edgecolor": "#C62828"},
    )

    # Panel 2: cycle diagram
    ax = axes[1]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Cykl oczekiwania", fontsize=FS_LABEL, fontweight="bold")

    # Thread boxes
    draw_box(
        ax,
        0.5,
        3.5,
        2.2,
        1.2,
        "Wątek A\ntrzyma Mutex 1",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )
    draw_box(
        ax,
        5.3,
        3.5,
        2.2,
        1.2,
        "Wątek B\ntrzyma Mutex 2",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )

    # Mutex boxes
    draw_box(
        ax, 0.5, 1.0, 2.2, 1.0, "Mutex 1", fill=GRAY3, fontsize=FS, fontweight="bold"
    )
    draw_box(
        ax, 5.3, 1.0, 2.2, 1.0, "Mutex 2", fill=GRAY3, fontsize=FS, fontweight="bold"
    )

    # holds arrows (down)
    draw_arrow(ax, 1.6, 3.5, 1.6, 2.0, lw=2)
    ax.text(0.9, 2.7, "trzyma", fontsize=FS_SMALL, rotation=90, va="center")
    draw_arrow(ax, 6.4, 3.5, 6.4, 2.0, lw=2)
    ax.text(7.0, 2.7, "trzyma", fontsize=FS_SMALL, rotation=90, va="center")

    # waits-for arrows (across, red)
    draw_arrow(ax, 2.7, 4.3, 5.3, 4.3, lw=2.5, color="#C62828")
    ax.text(
        4.0,
        4.7,
        "czeka na Mutex 2",
        fontsize=FS_SMALL,
        ha="center",
        fontweight="bold",
        color="#C62828",
    )
    draw_arrow(ax, 5.3, 3.7, 2.7, 3.7, lw=2.5, color="#C62828")
    ax.text(
        4.0,
        3.1,
        "czeka na Mutex 1",
        fontsize=FS_SMALL,
        ha="center",
        fontweight="bold",
        color="#C62828",
    )

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save_fig(fig, "q9_deadlock_scenario.png")


# ============================================================
# 12. Coffman conditions + prevention strategies
# ============================================================
def gen_coffman_strategies() -> None:
    """Gen coffman strategies."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.set_xlim(0, 11.5)
    ax.set_ylim(-3.5, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Warunki Coffmana — zapobieganie deadlockowi",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    headers = ["Warunek", "Opis", "Jak złamać", "Przykład"]
    col_w = [2.5, 2.5, 3.0, 3.0]
    rows = [
        [
            "1. Mutual Exclusion",
            "zasób wyłączny",
            "współdzielony zasób",
            "Read-write lock",
        ],
        [
            "2. Hold and Wait",
            "trzymaj + czekaj",
            "bierz WSZYSTKIE naraz",
            "lock(m1,m2) atomowo",
        ],
        [
            "3. No Preemption",
            "nie zabierzesz siłą",
            "timeout / trylock",
            "pthread_mutex_trylock()",
        ],
        [
            "4. Circular Wait",
            "cykliczne oczekiw.",
            "porządek liniowy",
            "zawsze m1 przed m2",
        ],
    ]
    draw_table(
        ax, headers, rows, x0=0.25, y0=0.5, col_widths=col_w, row_h=0.6, fontsize=7
    )

    ax.text(
        5.75,
        -3.1,
        "▸ Najczęstsza strategia: PORZĄDEK LINIOWY — "
        "numeruj mutexy, zawsze blokuj rosnąco",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    save_fig(fig, "q9_coffman_strategies.png")


# ============================================================
# 13. Starvation + Priority Inversion (2-panel)
# ============================================================
def gen_starvation_priority() -> None:
    """Gen starvation priority."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle(
        "Zagłodzenie i Inwersja priorytetów", fontsize=FS_TITLE, fontweight="bold"
    )

    # Panel 1: Starvation + aging
    ax = axes[0]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Zagłodzenie (Starvation)", fontsize=FS_LABEL, fontweight="bold")

    threads = [
        ("Wątek HIGH", "prio=10", GRAY5, 3.0),
        ("Wątek HIGH", "prio=9", GRAY3, 2.2),
        ("Wątek MED", "prio=5", GRAY2, 1.4),
        ("Wątek LOW", "prio=1 → głoduje!", "#F8D7DA", 0.6),
    ]
    for name, prio, color, y in threads:
        draw_box(
            ax, 0.5, y, 2.0, 0.6, name, fill=color, fontsize=FS_SMALL, fontweight="bold"
        )
        ax.text(2.8, y + 0.3, prio, fontsize=FS_SMALL, va="center")

    ax.text(
        1.5,
        4.2,
        "CPU zawsze\ndostaje HIGH!",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )
    draw_arrow(ax, 1.5, 3.9, 1.5, 3.65, lw=1.5)

    # Aging solution
    draw_box(ax, 4.5, 1.5, 3.2, 2.5, "", fill=GRAY4, rounded=True)
    ax.text(6.1, 3.7, "Rozwiązanie: AGING", fontsize=FS, fontweight="bold", ha="center")
    aging = [
        "t=0:    prio=1",
        "t=100ms: prio=2",
        "t=200ms: prio=3",
        "...",
        "w końcu → CPU!",
    ]
    for i, line in enumerate(aging):
        ax.text(
            6.1, 3.2 - i * 0.4, line, fontsize=FS_SMALL, ha="center", family="monospace"
        )

    # Panel 2: Priority Inversion
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Inwersja priorytetów", fontsize=FS_LABEL, fontweight="bold")

    # Timeline
    labels = ["H (wysoki)", "M (średni)", "L (niski)"]
    ys = [4.2, 2.8, 1.4]
    for label, y in zip(labels, ys, strict=False):
        ax.text(0.3, y + 0.2, label, fontsize=FS, fontweight="bold", va="center")

    # L runs and locks mutex
    draw_box(ax, 2.0, ys[2], 1.2, 0.5, "lock(m)", fill=GRAY1, fontsize=FS_SMALL)

    # M preempts L
    draw_box(ax, 3.5, ys[1], 3.0, 0.5, "M pracuje...", fill=GRAY3, fontsize=FS_SMALL)

    # H waits for mutex
    draw_box(
        ax,
        3.5,
        ys[0],
        3.0,
        0.5,
        "CZEKA na mutex!",
        fill="#F8D7DA",
        fontsize=FS_SMALL,
        fontweight="bold",
    )

    # M finishes, L continues, unlocks
    draw_box(ax, 6.8, ys[2], 1.5, 0.5, "unlock(m)", fill=GRAY1, fontsize=FS_SMALL)
    draw_box(ax, 8.5, ys[0], 1.2, 0.5, "H runs", fill=GRAY4, fontsize=FS_SMALL)

    # Explanation
    ax.text(
        5.0,
        0.5,
        "H czeka na M (mimo H > M)!\n"
        "Rozwiązanie: Priority Inheritance\n"
        "L dziedziczy priorytet H → M nie wypycha L",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.text(
        5.0,
        0.0,
        "Mars Pathfinder (1997) — klasyczny bug!",
        fontsize=FS_SMALL,
        ha="center",
        fontweight="bold",
    )

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save_fig(fig, "q9_starvation_priority.png")
