"""Q9 diagrams 1-6: process/thread basics, memory, states, PCB, speed."""

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
# 1. Process vs Thread comparison table
# ============================================================
def gen_process_vs_thread() -> None:
    """Gen process vs thread."""
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(-4.5, 1.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Proces vs Wątek — porównanie", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    headers = ["Cecha", "Proces", "Wątek"]
    col_w = [2.5, 3.5, 3.5]
    rows = [
        ["Pamięć", "Własna, izolowana", "Współdzielona (heap)"],
        ["Tworzenie", "~1-10 ms", "~10-100 μs (100x szybciej)"],
        ["Przełączanie", "~1-5 μs (TLB flush)", "~0.1-0.5 μs (10x)"],
        ["Komunikacja", "IPC (pipe, socket, shm)", "Bezpośrednia (wspólna pam.)"],
        ["Izolacja", "Pełna — awaria izolowana", "Brak — może zabić proces"],
        ["Zastosowanie", "Bezpieczeństwo, izolacja", "Wydajność, współdzielenie"],
    ]
    draw_table(
        ax,
        headers,
        rows,
        x0=0.25,
        y0=0.8,
        col_widths=col_w,
        row_h=0.55,
        fontsize=7.5,
        header_fontsize=FS_LABEL,
    )

    # Analogy at bottom
    ax.text(
        5.0,
        -4.2,
        "Analogia:  Proces = mieszkanie (własny adres)     "
        "Wątek = pokój w mieszkaniu (wspólna kuchnia = heap)",
        ha="center",
        fontsize=FS,
        style="italic",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    save_fig(fig, "q9_process_vs_thread.png")


# ============================================================
# 2. Memory segments layout
# ============================================================
def gen_memory_layout() -> None:
    """Gen memory layout."""
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Segmenty pamięci procesu", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    segments = [
        ("STACK ↓", "zmienne lokalne, adresy\npowrotu (każdy wątek WŁASNY)", GRAY1),
        ("...", "(wolna przestrzeń)", "white"),
        ("HEAP ↑", "malloc/new — dynamiczna\nalokacja (współdzielony)", GRAY4),
        ("BSS", "zmienne globalne\nniezainicjalizowane (zerowane)", GRAY2),
        ("DATA", "zmienne globalne\nzainicjalizowane", GRAY3),
        ("TEXT", "kod maszynowy\n(read-only, współdzielony)", GRAY5),
    ]
    bx, bw = 2.0, 2.5
    seg_h = 0.9
    gap = 0.05
    top_y = 7.0

    for i, (name, desc, color) in enumerate(segments):
        y = top_y - i * (seg_h + gap)
        draw_box(
            ax,
            bx,
            y,
            bw,
            seg_h,
            name,
            fill=color,
            fontsize=FS_LABEL,
            fontweight="bold",
            rounded=False,
        )
        ax.text(bx + bw + 0.3, y + seg_h / 2, desc, fontsize=7.5, va="center")

    # Address labels
    ax.text(
        bx - 0.2,
        top_y + seg_h / 2,
        "wysoki\nadres",
        fontsize=FS_SMALL,
        va="center",
        ha="right",
        style="italic",
    )
    bottom_y = top_y - 5 * (seg_h + gap)
    ax.text(
        bx - 0.2,
        bottom_y + seg_h / 2,
        "niski\nadres",
        fontsize=FS_SMALL,
        va="center",
        ha="right",
        style="italic",
    )

    # Arrows for growth
    ax.annotate(
        "",
        xy=(bx - 0.5, top_y - 0.1),
        xytext=(bx - 0.5, top_y + seg_h + 0.1),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(bx - 0.9, top_y + 0.4, "rośnie\nw dół", fontsize=FS_SMALL, ha="center")

    heap_y = top_y - 2 * (seg_h + gap)
    ax.annotate(
        "",
        xy=(bx - 0.5, heap_y + seg_h + 0.1),
        xytext=(bx - 0.5, heap_y - 0.1),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(bx - 0.9, heap_y + 0.5, "rośnie\nw górę", fontsize=FS_SMALL, ha="center")

    save_fig(fig, "q9_memory_layout.png")


# ============================================================
# 3. Process states diagram
# ============================================================
def gen_process_states() -> None:
    """Gen process states."""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Stany procesu — diagram przejść", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    states = {
        "NEW": (1.0, 2.5),
        "READY": (3.5, 2.5),
        "RUNNING": (6.5, 2.5),
        "BLOCKED": (6.5, 0.5),
        "TERMINATED": (10.0, 2.5),
    }
    fills = {
        "NEW": GRAY4,
        "READY": GRAY1,
        "RUNNING": GRAY3,
        "BLOCKED": GRAY2,
        "TERMINATED": GRAY5,
    }
    bw, bh = 1.8, 0.9
    for name, (x, y) in states.items():
        draw_box(
            ax,
            x,
            y,
            bw,
            bh,
            name,
            fill=fills[name],
            fontsize=FS_LABEL,
            fontweight="bold",
        )

    # Transitions
    transitions = [
        ("NEW", "READY", "admit"),
        ("READY", "RUNNING", "dispatch\n(scheduler)"),
        ("RUNNING", "TERMINATED", "exit"),
        ("RUNNING", "BLOCKED", "I/O wait"),
    ]
    for src, dst, label in transitions:
        sx, sy = states[src]
        dx, dy = states[dst]
        if sy == dy:  # horizontal
            draw_arrow(ax, sx + bw, sy + bh / 2, dx, dy + bh / 2, lw=1.5)
            mx = (sx + bw + dx) / 2
            ax.text(
                mx,
                sy + bh / 2 + 0.25,
                label,
                fontsize=FS_SMALL,
                ha="center",
                va="bottom",
            )
        else:  # vertical
            draw_arrow(ax, sx + bw / 2, sy, dx + bw / 2, dy + bh, lw=1.5)
            ax.text(
                sx + bw + 0.2,
                (sy + dy + bh) / 2,
                label,
                fontsize=FS_SMALL,
                ha="left",
                va="center",
            )

    # BLOCKED → READY
    bx, by = states["BLOCKED"]
    rx, ry = states["READY"]
    ax.annotate(
        "",
        xy=(rx + bw / 2, ry),
        xytext=(bx - 0.3, by + bh / 2),
        arrowprops={
            "arrowstyle": "->",
            "lw": 1.5,
            "color": LN,
            "connectionstyle": "arc3,rad=0.3",
        },
    )
    ax.text(3.5, 0.7, "I/O done", fontsize=FS_SMALL, ha="center")

    # RUNNING → READY (preemption)
    rux, ruy = states["RUNNING"]
    draw_arrow(ax, rux, ruy + bh, rx + bw, ry + bh, lw=1.2)
    ax.text(5.0, 3.7, "preempt /\ntimeout", fontsize=FS_SMALL, ha="center")

    save_fig(fig, "q9_process_states.png")


# ============================================================
# 4. Thread structure within process
# ============================================================
def gen_thread_structure() -> None:
    """Gen thread structure."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Wątki wewnątrz procesu (PID=42)", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    # Shared memory region
    draw_box(ax, 0.5, 3.5, 9.0, 1.8, "", fill=GRAY1, rounded=False, lw=2)
    ax.text(5.0, 5.0, "WSPÓŁDZIELONE", fontsize=FS, fontweight="bold", ha="center")

    labels_shared = ["TEXT", "DATA", "BSS", "HEAP", "pliki", "PID"]
    for i, lab in enumerate(labels_shared):
        x = 1.0 + i * 1.4
        draw_box(
            ax,
            x,
            3.8,
            1.1,
            0.6,
            lab,
            fill=GRAY3,
            fontsize=FS,
            fontweight="bold",
            rounded=False,
        )
        ax.text(x + 0.55, 4.6, lab, fontsize=FS_SMALL, ha="center", color="#555555")

    # Per-thread regions
    draw_box(
        ax, 0.5, 0.5, 9.0, 2.7, "", fill="white", rounded=False, lw=2, linestyle="--"
    )
    ax.text(
        5.0, 2.95, "PRYWATNE (każdy wątek)", fontsize=FS, fontweight="bold", ha="center"
    )

    for i in range(3):
        x = 1.0 + i * 3.0
        tid = i + 1
        draw_box(ax, x, 0.7, 2.3, 2.0, "", fill=GRAY4, rounded=False)
        ax.text(
            x + 1.15,
            2.4,
            f"Wątek {tid}",
            fontsize=FS_LABEL,
            fontweight="bold",
            ha="center",
        )
        items = [f"stos_{tid}", f"rejestry_{tid}", f"PC_{tid}", f"TID={40 + tid}"]
        for j, item in enumerate(items):
            ax.text(
                x + 1.15,
                2.0 - j * 0.35,
                item,
                fontsize=FS_SMALL,
                ha="center",
                family="monospace",
            )

    save_fig(fig, "q9_thread_structure.png")


# ============================================================
# 5. PCB structure
# ============================================================
def gen_pcb_structure() -> None:
    """Gen pcb structure."""
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "PCB (Process Control Block)", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    fields = [
        ("PID", "42"),
        ("Stan", "READY / RUNNING / BLOCKED"),
        ("Rejestry CPU", "EAX, EBX, ESP, EIP ..."),
        ("Tablice stron", "mapowanie wirtualne → fizyczne"),
        ("Otwarte pliki", "fd[0], fd[1], fd[2] ..."),
        ("Priorytety", "nice value, scheduling class"),
        ("Statystyki", "CPU time, I/O count"),
    ]

    top_y = 4.8
    for i, (field, value) in enumerate(fields):
        y = top_y - i * 0.55
        draw_box(
            ax,
            0.5,
            y,
            2.2,
            0.45,
            field,
            fill=GRAY2,
            fontsize=FS,
            fontweight="bold",
            rounded=False,
        )
        draw_box(ax, 2.7, y, 4.5, 0.45, value, fill=GRAY4, fontsize=FS, rounded=False)

    ax.text(
        4.0,
        0.3,
        "Context switch = zapisz PCB starego → wczytaj PCB nowego",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
    )

    save_fig(fig, "q9_pcb_structure.png")


# ============================================================
# 6. Speed comparison
# ============================================================
def gen_speed_comparison() -> None:
    """Gen speed comparison."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    fig.suptitle(
        "Szybkość — procesy vs wątki (benchmarki Linux)",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    # Creation time panel
    ax = axes[0]
    ops = ["fork()\n(nowy proces)", "pthread_create()\n(nowy wątek)"]
    times = [3.0, 0.05]  # ms
    colors = [GRAY3, GRAY1]
    bars = ax.barh(ops, times, color=colors, edgecolor=LN, height=0.5, linewidth=1.2)
    ax.set_xlabel("Czas [ms]", fontsize=FS)
    ax.set_title("Tworzenie", fontsize=FS_LABEL, fontweight="bold")
    ax.set_xlim(0, 4.5)
    for bar, t in zip(bars, times, strict=False):
        ax.text(
            bar.get_width() + 0.1,
            bar.get_y() + bar.get_height() / 2,
            f"{t} ms",
            va="center",
            fontsize=FS,
        )
    ax.text(
        2.5,
        -0.6,
        "~100x szybciej",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        transform=ax.get_xaxis_transform(),
    )
    ax.tick_params(labelsize=FS)

    # Right: context switch
    ax = axes[1]
    ops2 = ["Proces→Proces\n(TLB flush)", "Wątek→Wątek\n(TLB warm)"]
    times2 = [3000, 300]  # ns
    bars2 = ax.barh(ops2, times2, color=colors, edgecolor=LN, height=0.5, linewidth=1.2)
    ax.set_xlabel("Czas [ns]", fontsize=FS)
    ax.set_title("Przełączanie kontekstu", fontsize=FS_LABEL, fontweight="bold")
    ax.set_xlim(0, 4500)
    for bar, t in zip(bars2, times2, strict=False):
        ax.text(
            bar.get_width() + 50,
            bar.get_y() + bar.get_height() / 2,
            f"{t} ns",
            va="center",
            fontsize=FS,
        )
    ax.text(
        2500,
        -0.6,
        "~10x szybciej",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        transform=ax.get_xaxis_transform(),
    )
    ax.tick_params(labelsize=FS)

    fig.tight_layout(rect=[0, 0.05, 1, 0.92])
    save_fig(fig, "q9_speed_comparison.png")
