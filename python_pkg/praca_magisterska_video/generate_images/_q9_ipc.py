"""Q9 diagrams 7-9: IPC mechanisms and scenario tables."""

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
    draw_arrow,
    draw_box,
    draw_double_arrow,
    draw_table,
    save_fig,
)
import matplotlib.pyplot as plt


# ============================================================
# 7. Scenario table (when to use process vs thread)
# ============================================================
def gen_scenario_table() -> None:
    """Gen scenario table."""
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.set_xlim(0, 11)
    ax.set_ylim(-5.5, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Kiedy proces, kiedy wątek? — typowe scenariusze",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    headers = ["Scenariusz", "Wybór", "Dlaczego?"]
    col_w = [3.5, 2.5, 4.5]
    rows = [
        ["Serwer WWW (Apache)", "Proces", "izolacja klientów"],
        ["Serwer WWW (nginx)", "Wątek / async", "szybkość, cooperacja"],
        ["Przeglądarka (karty)", "Proces", "crash isolation"],
        ["Przeglądarka (JS+render)", "Wątek", "współdzielony DOM"],
        ["Gra (fizyka+rendering)", "Wątek", "współdzielony świat gry"],
        ["Kompilacja (make -j8)", "Proces", "izolacja, prostota"],
        ["Baza danych (zapytania)", "Wątek", "współdzielony cache"],
        ["Microservices", "Proces (kontener)", "izolacja, deployment"],
    ]
    draw_table(
        ax, headers, rows, x0=0.25, y0=0.5, col_widths=col_w, row_h=0.5, fontsize=7
    )

    save_fig(fig, "q9_scenario_table.png")


# ============================================================
# 8. IPC details: pipe, shared memory, socket (3-panel)
# ============================================================
def gen_ipc_details() -> None:
    """Gen ipc details."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
    fig.suptitle("Mechanizmy IPC — szczegóły", fontsize=FS_TITLE, fontweight="bold")

    # Panel 1: Pipe
    ax = axes[0]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Pipe (potok)", fontsize=FS_LABEL, fontweight="bold")

    draw_box(ax, 0.2, 2.0, 1.8, 1.2, "Proces A\n(ls)\nstdout", fill=GRAY1, fontsize=FS)
    draw_box(
        ax,
        3.0,
        2.0,
        1.8,
        1.2,
        "Bufor\njądra\n(4 KB)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )
    draw_box(ax, 5.8, 2.0, 1.8, 1.2, "Proces B\n(grep)\nstdin", fill=GRAY1, fontsize=FS)
    draw_arrow(ax, 2.0, 2.6, 3.0, 2.6, lw=1.5)
    ax.text(2.5, 3.0, "write()\nfd[1]", fontsize=FS_SMALL, ha="center")
    draw_arrow(ax, 4.8, 2.6, 5.8, 2.6, lw=1.5)
    ax.text(5.3, 3.0, "read()\nfd[0]", fontsize=FS_SMALL, ha="center")
    ax.text(
        4.0,
        0.8,
        "Jednokierunkowy\nBufor pełny → write() blokuje",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # Panel 2: Shared Memory
    ax = axes[1]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Shared Memory", fontsize=FS_LABEL, fontweight="bold")

    draw_box(ax, 0.3, 3.0, 2.2, 1.2, "Proces A\nstrona 7", fill=GRAY1, fontsize=FS)
    draw_box(ax, 5.5, 3.0, 2.2, 1.2, "Proces B\nstrona 3", fill=GRAY1, fontsize=FS)
    draw_box(
        ax,
        2.8,
        1.0,
        2.4,
        1.2,
        "RAM\nramka 42",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 2.0, 3.0, 3.5, 2.2, lw=1.5)
    draw_arrow(ax, 6.0, 3.0, 4.5, 2.2, lw=1.5)
    ax.text(
        4.0,
        0.3,
        "Zero kopiowania!\nA pisze → B widzi od razu\nWymaga synchronizacji (semafor)",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # Panel 3: Socket
    ax = axes[2]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Socket", fontsize=FS_LABEL, fontweight="bold")

    # Network socket
    draw_box(
        ax, 0.3, 3.2, 1.8, 0.9, "Klient", fill=GRAY1, fontsize=FS, fontweight="bold"
    )
    draw_box(
        ax, 5.5, 3.2, 1.8, 0.9, "Serwer", fill=GRAY1, fontsize=FS, fontweight="bold"
    )
    draw_double_arrow(ax, 2.1, 3.65, 5.5, 3.65, lw=1.5)
    ax.text(3.8, 4.3, "TCP/IP (sieciowy)", fontsize=FS, ha="center", fontweight="bold")

    # Unix socket
    draw_box(
        ax, 0.3, 1.3, 1.8, 0.9, "Proces A", fill=GRAY4, fontsize=FS, fontweight="bold"
    )
    draw_box(
        ax, 5.5, 1.3, 1.8, 0.9, "Proces B", fill=GRAY4, fontsize=FS, fontweight="bold"
    )
    draw_double_arrow(ax, 2.1, 1.75, 5.5, 1.75, lw=1.5)
    ax.text(
        3.8,
        2.4,
        "Unix domain socket\n(/tmp/app.sock)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )

    ax.text(
        3.8,
        0.5,
        "Dwukierunkowy\nNajbardziej uniwersalny IPC",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save_fig(fig, "q9_ipc_details.png")


# ============================================================
# 9. IPC comparison table
# ============================================================
def gen_ipc_table() -> None:
    """Gen ipc table."""
    fig, ax = plt.subplots(figsize=(8.5, 3.5))
    ax.set_xlim(0, 11)
    ax.set_ylim(-4.5, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Porównanie mechanizmów IPC", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    headers = ["Mechanizm", "Kierunek", "Szybkość", "Zastosowanie"]
    col_w = [2.5, 2.0, 2.5, 3.5]
    rows = [
        ["Pipe", "jednokierunkowy", "średnia", "ls | grep"],
        ["Named Pipe", "jednokierunkowy", "średnia", "demon → klient"],
        ["Shared Memory", "dwukierunkowy", "NAJSZYBSZA", "video, bazy danych"],
        ["Message Queue", "dwukierunkowy", "średnia", "wieloproducentowe"],
        ["Socket", "dwukierunkowy", "wolna (sieć)", "klient-serwer"],
        ["Signal", "jednokierunkowy", "natychmiastowa", "powiadomienia (nr)"],
    ]
    draw_table(
        ax, headers, rows, x0=0.25, y0=0.5, col_widths=col_w, row_h=0.5, fontsize=7.5
    )

    save_fig(fig, "q9_ipc_table.png")
