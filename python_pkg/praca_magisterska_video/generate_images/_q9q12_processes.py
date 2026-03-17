"""PYTANIE 9 diagrams: IPC, deadlock, producer-consumer."""

from __future__ import annotations

import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._q9q12_common import (
    _LAST_CONDITION_INDEX,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LIGHT_BLUE,
    LIGHT_GREEN,
    LIGHT_ORANGE,
    LIGHT_RED,
    LIGHT_YELLOW,
    LN,
    draw_arrow,
    draw_box,
    save_fig,
)


def gen_ipc_mechanisms() -> None:
    """IPC mechanisms comparison diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Mechanizmy IPC — porównanie", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    mechanisms = [
        (
            "Pipe",
            "→ jednokierunkowy\n→ bufor w jądrze\n→ spokrewnione procesy",
            "ls | grep txt",
            GRAY1,
        ),
        (
            "Shared\nMemory",
            "→ wspólna ramka RAM\n→ zero kopiowania\n→ wymaga synchronizacji",
            "mmap() / shm_open()",
            LIGHT_GREEN,
        ),
        (
            "Message\nQueue",
            "→ strukturalne wiad.\n→ asynchroniczna\n→ filtrowanie typów",
            "msgsnd() / msgrcv()",
            LIGHT_BLUE,
        ),
        (
            "Socket",
            "→ dwukierunkowy\n→ lokalny lub sieciowy\n→ TCP/UDP",
            "connect() / accept()",
            LIGHT_YELLOW,
        ),
    ]

    for i, (name, desc, example, color) in enumerate(mechanisms):
        x = 0.3
        y = 5.5 - i * 1.5
        # Box for mechanism name
        draw_box(ax, x, y, 1.5, 1.0, name, fill=color, fontsize=9, fontweight="bold")
        # Description
        ax.text(
            x + 2.0,
            y + 0.5,
            desc,
            fontsize=FS,
            va="center",
            ha="left",
            family="monospace",
        )
        # Example
        draw_box(ax, 6.5, y + 0.15, 3.0, 0.7, example, fill=GRAY4, fontsize=FS_SMALL)

    # Draw process boxes for pipe illustration at top
    y_top = 6.3
    ax.text(
        5.0,
        y_top,
        "Proces A  ──bufor jądra──▶  Proces B",
        fontsize=FS,
        ha="center",
        va="center",
        family="monospace",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY1, "edgecolor": GRAY3},
    )

    # Legend
    ax.text(
        0.3,
        0.3,
        "Szybkość: Shared Memory > Pipe ≈ MsgQueue > Socket (sieciowy)",
        fontsize=FS,
        va="center",
        style="italic",
    )

    save_fig(fig, "ipc_mechanisms.png")


def gen_deadlock_illustration() -> None:
    """Deadlock circular wait diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Zakleszczenie (Deadlock) — cykliczne oczekiwanie",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Thread boxes
    draw_box(
        ax,
        0.5,
        3.5,
        2.0,
        1.2,
        "Wątek A\n(trzyma Mutex 1)",
        fill=LIGHT_BLUE,
        fontsize=9,
        fontweight="bold",
    )
    draw_box(
        ax,
        5.5,
        3.5,
        2.0,
        1.2,
        "Wątek B\n(trzyma Mutex 2)",
        fill=LIGHT_ORANGE,
        fontsize=9,
        fontweight="bold",
    )

    # Resource boxes
    draw_box(
        ax,
        0.5,
        0.8,
        2.0,
        1.0,
        "Mutex 1\nzablokowany",
        fill=GRAY2,
        fontsize=8,
        fontweight="bold",
    )
    draw_box(
        ax,
        5.5,
        0.8,
        2.0,
        1.0,
        "Mutex 2\nzablokowany",
        fill=GRAY2,
        fontsize=8,
        fontweight="bold",
    )

    # Hold arrows (downward)
    draw_arrow(ax, 1.5, 3.5, 1.5, 1.8, lw=2.0, color="#333333")
    ax.text(0.3, 2.65, "trzyma", fontsize=FS, ha="center", rotation=90, color="#333333")

    draw_arrow(ax, 6.5, 3.5, 6.5, 1.8, lw=2.0, color="#333333")
    ax.text(7.7, 2.65, "trzyma", fontsize=FS, ha="center", rotation=90, color="#333333")

    # Arrows: "waits for" (across, with red)
    draw_arrow(ax, 2.5, 4.3, 5.5, 4.3, lw=2.5, color="#C62828")
    ax.text(
        4.0,
        4.6,
        "czeka na Mutex 2",
        fontsize=FS,
        ha="center",
        color="#C62828",
        fontweight="bold",
    )

    draw_arrow(ax, 5.5, 3.7, 2.5, 3.7, lw=2.5, color="#C62828")
    ax.text(
        4.0,
        3.2,
        "czeka na Mutex 1",
        fontsize=FS,
        ha="center",
        color="#C62828",
        fontweight="bold",
    )

    # Coffman conditions
    conditions = [
        "1. Mutual Exclusion — zasoby wyłączne",
        "2. Hold and Wait — trzymaj + czekaj",
        "3. No Preemption — nie można zabrać siłą",
        "4. Circular Wait — cykl oczekiwania ← złam ten!",
    ]
    for i, cond in enumerate(conditions):
        color_c = "#C62828" if i == _LAST_CONDITION_INDEX else LN
        fw = "bold" if i == _LAST_CONDITION_INDEX else "normal"
        ax.text(
            0.5,
            0.5 - i * 0.25 + 0.2,
            cond,
            fontsize=FS_SMALL,
            color=color_c,
            fontweight=fw,
            va="center",
        )

    save_fig(fig, "deadlock_illustration.png")


def gen_producer_consumer() -> None:
    """Producer-consumer with bounded buffer diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Producent-Konsument z buforem cyklicznym (N=4)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Producer
    draw_box(
        ax,
        0.3,
        2.0,
        1.8,
        1.5,
        "Producent\n\nwstaw(elem)\nV(full)\nV(mutex)",
        fill=LIGHT_GREEN,
        fontsize=FS,
        fontweight="bold",
    )

    # Buffer slots
    buf_x = 3.0
    buf_y = 2.5
    slot_w = 1.0
    slot_h = 0.8
    items = ["A", "B", "", ""]
    fills = [LIGHT_BLUE, LIGHT_BLUE, "white", "white"]
    for i, (item, fc) in enumerate(zip(items, fills, strict=False)):
        x = buf_x + i * slot_w
        draw_box(
            ax,
            x,
            buf_y,
            slot_w,
            slot_h,
            item,
            fill=fc,
            fontsize=10,
            fontweight="bold",
            rounded=False,
        )

    ax.text(
        buf_x + 2.0,
        buf_y + slot_h + 0.3,
        "Bufor (N=4)",
        fontsize=9,
        ha="center",
        fontweight="bold",
    )
    ax.text(
        buf_x + 2.0,
        buf_y - 0.3,
        "full=2, empty=2",
        fontsize=FS,
        ha="center",
        family="monospace",
    )

    # Consumer
    draw_box(
        ax,
        7.8,
        2.0,
        1.8,
        1.5,
        "Konsument\n\npobierz()\nV(empty)\nV(mutex)",
        fill=LIGHT_YELLOW,
        fontsize=FS,
        fontweight="bold",
    )

    # Arrows
    draw_arrow(ax, 2.1, 2.75, 3.0, 2.9, lw=1.5)
    draw_arrow(ax, 7.0, 2.9, 7.8, 2.75, lw=1.5)

    # Semaphores
    sems = [
        ("mutex = 1", "wyłączny dostęp do bufora", GRAY2),
        ("empty = 2", "wolne sloty (P = czekaj, V = +1)", LIGHT_GREEN),
        ("full = 2", "pełne sloty (P = czekaj, V = +1)", LIGHT_BLUE),
    ]
    for i, (name, desc, color) in enumerate(sems):
        y = 1.2 - i * 0.45
        draw_box(
            ax,
            3.0,
            y,
            1.5,
            0.35,
            name,
            fill=color,
            fontsize=FS_SMALL,
            fontweight="bold",
        )
        ax.text(4.7, y + 0.17, desc, fontsize=FS_SMALL, va="center")

    # Warning
    ax.text(
        0.3,
        4.8,
        "KOLEJNOŚĆ: P(empty/full) PRZED P(mutex)!  Odwrotnie = DEADLOCK",
        fontsize=FS,
        fontweight="bold",
        color="#C62828",
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": LIGHT_RED,
            "edgecolor": "#C62828",
        },
    )

    save_fig(fig, "producer_consumer.png")
