#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 1: Automata and language classes.

  1. FA recognition example — DFA for strings ending in "ab"
  2. PDA recognition example — PDA for aⁿbⁿ
  3. LBA recognition example — LBA for aⁿbⁿcⁿ
  4. TM recognition example — TM for 0ⁿ1ⁿ.

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
FS_SMALL = 6.5
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"
LIGHT_GREEN = "#D5E8D4"
LIGHT_RED = "#F8D7DA"
LIGHT_BLUE = "#D6EAF8"
LIGHT_YELLOW = "#FFF9C4"

INNER_RATIO = 0.82
ARROW_OFFSET = 0.4
LOOP_RAD = 1.8
LOOP_OFFSET = 0.12
LOOP_LABEL_OFFSET = 0.35
MUTATION_SCALE = 12
HEAD_MARKER_FONTSIZE = 8


@dataclass(frozen=True)
class StateStyle:
    """Optional styling for automaton state circles."""

    accepting: bool = False
    initial: bool = False
    fillcolor: str = "white"
    fontsize: float = FS


@dataclass(frozen=True)
class ArrowStyle:
    """Optional styling for curved arrows."""

    connectionstyle: str = "arc3,rad=0.3"
    fontsize: float = FS_SMALL
    label_offset: tuple[float, float] = (0, 0)


@dataclass(frozen=True)
class LoopStyle:
    """Optional styling for self-loops."""

    direction: str = "top"
    fontsize: float = FS_SMALL


def draw_state_circle(
    ax: Axes,
    pos: tuple[float, float],
    r: float,
    label: str,
    style: StateStyle | None = None,
) -> None:
    """Draw an automaton state circle."""
    s = style or StateStyle()
    x, y = pos
    circle = plt.Circle(
        (x, y),
        r,
        fill=True,
        facecolor=s.fillcolor,
        edgecolor=LN,
        linewidth=1.5,
        zorder=3,
    )
    ax.add_patch(circle)
    if s.accepting:
        inner = plt.Circle(
            (x, y),
            r * INNER_RATIO,
            fill=False,
            edgecolor=LN,
            linewidth=1.2,
            zorder=3,
        )
        ax.add_patch(inner)
    if s.initial:
        ax.annotate(
            "",
            xy=(x - r, y),
            xytext=(x - r - ARROW_OFFSET, y),
            arrowprops={
                "arrowstyle": "->",
                "color": LN,
                "lw": 1.5,
            },
            zorder=4,
        )
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=s.fontsize,
        fontweight="bold",
        zorder=5,
    )


def draw_curved_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str,
    style: ArrowStyle | None = None,
) -> None:
    """Draw a curved arrow between points with label."""
    s = style or ArrowStyle()
    x1, y1 = start
    x2, y2 = end
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={
            "arrowstyle": "->",
            "color": LN,
            "lw": 1.2,
            "connectionstyle": s.connectionstyle,
        },
        zorder=2,
    )
    mx = (x1 + x2) / 2 + s.label_offset[0]
    my = (y1 + y2) / 2 + s.label_offset[1]
    ax.text(
        mx,
        my,
        label,
        ha="center",
        va="center",
        fontsize=s.fontsize,
        fontstyle="italic",
        zorder=5,
        bbox={
            "boxstyle": "round,pad=0.15",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.9,
        },
    )


def draw_self_loop(
    ax: Axes,
    pos: tuple[float, float],
    r: float,
    label: str,
    style: LoopStyle | None = None,
) -> None:
    """Draw a self-loop on a state."""
    s = style or LoopStyle()
    x, y = pos
    if s.direction == "top":
        loop = mpatches.FancyArrowPatch(
            (x - LOOP_OFFSET, y + r),
            (x + LOOP_OFFSET, y + r),
            connectionstyle=f"arc3,rad=-{LOOP_RAD}",
            arrowstyle="->",
            mutation_scale=MUTATION_SCALE,
            lw=1.2,
            color=LN,
            zorder=2,
        )
        ax.add_patch(loop)
        ax.text(
            x,
            y + r + LOOP_LABEL_OFFSET,
            label,
            ha="center",
            va="center",
            fontsize=s.fontsize,
            fontstyle="italic",
            zorder=5,
        )
    elif s.direction == "bottom":
        loop = mpatches.FancyArrowPatch(
            (x - LOOP_OFFSET, y - r),
            (x + LOOP_OFFSET, y - r),
            connectionstyle=f"arc3,rad={LOOP_RAD}",
            arrowstyle="->",
            mutation_scale=MUTATION_SCALE,
            lw=1.2,
            color=LN,
            zorder=2,
        )
        ax.add_patch(loop)
        ax.text(
            x,
            y - r - LOOP_LABEL_OFFSET,
            label,
            ha="center",
            va="center",
            fontsize=s.fontsize,
            fontstyle="italic",
            zorder=5,
        )


# ============================================================
# 1. FA Recognition Example — DFA for strings ending in "ab"
# ============================================================
def draw_fa_recognition() -> None:
    """FA state diagram + step-by-step trace for 'baab'."""
    _fig, axes = plt.subplots(
        1,
        2,
        figsize=(11.69, 4),
        gridspec_kw={"width_ratios": [1, 1.3]},
    )

    # --- Left: State diagram ---
    ax = axes[0]
    ax.set_xlim(-1, 5.5)
    ax.set_ylim(-1.5, 2.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "DFA — diagram stanów\n"
        'L = {słowa nad {a,b} kończące się na "ab"}',
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    state_r = 0.35
    states = {
        "q₀": (0.8, 0.5),
        "q₁": (2.8, 0.5),
        "q₂": (4.8, 0.5),
    }

    draw_state_circle(
        ax,
        states["q₀"],
        state_r,
        "q₀",
        StateStyle(initial=True),
    )
    draw_state_circle(ax, states["q₁"], state_r, "q₁")
    draw_state_circle(
        ax,
        states["q₂"],
        state_r,
        "q₂",
        StateStyle(
            accepting=True, fillcolor=LIGHT_GREEN
        ),
    )

    # Transitions
    # q₀ --a--> q₁
    draw_curved_arrow(
        ax,
        (states["q₀"][0] + state_r, states["q₀"][1] + 0.05),
        (states["q₁"][0] - state_r, states["q₁"][1] + 0.05),
        "a",
        ArrowStyle(
            connectionstyle="arc3,rad=0.15",
            label_offset=(0, 0.25),
        ),
    )
    # q₁ --b--> q₂
    draw_curved_arrow(
        ax,
        (states["q₁"][0] + state_r, states["q₁"][1] + 0.05),
        (states["q₂"][0] - state_r, states["q₂"][1] + 0.05),
        "b",
        ArrowStyle(
            connectionstyle="arc3,rad=0.15",
            label_offset=(0, 0.25),
        ),
    )
    # q₂ --a--> q₁
    draw_curved_arrow(
        ax,
        (states["q₂"][0] - state_r, states["q₂"][1] - 0.05),
        (states["q₁"][0] + state_r, states["q₁"][1] - 0.05),
        "a",
        ArrowStyle(
            connectionstyle="arc3,rad=0.15",
            label_offset=(0, -0.3),
        ),
    )
    # q₂ --b--> q₀
    draw_curved_arrow(
        ax,
        (states["q₂"][0] - 0.2, states["q₂"][1] - state_r),
        (states["q₀"][0] + 0.2, states["q₀"][1] - state_r),
        "b",
        ArrowStyle(
            connectionstyle="arc3,rad=0.4",
            label_offset=(0, -0.4),
        ),
    )
    # q₀ --b--> q₀ (self-loop)
    draw_self_loop(
        ax,
        states["q₀"],
        state_r,
        "b",
        LoopStyle(direction="top"),
    )
    # q₁ --a--> q₁ (self-loop)
    draw_self_loop(
        ax,
        states["q₁"],
        state_r,
        "a",
        LoopStyle(direction="top"),
    )

    # Legend
    ax.text(
        0.3,
        -1.0,
        "→ = start    ◎ = akceptujący",
        fontsize=FS_SMALL,
        ha="left",
        va="center",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    # --- Right: Step-by-step trace ---
    ax2 = axes[1]
    ax2.axis("off")
    ax2.set_title(
        'Ślad wykonania — wejście: "baab"',
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    trace_data = [
        [
            "Krok",
            "Czytam",
            "Stan przed",
            "Przejście",
            "Stan po",
        ],
        ["—", "—", "q₀ (start)", "—", "q₀"],
        ["1", "b", "q₀", "δ(q₀, b) = q₀", "q₀"],
        ["2", "a", "q₀", "δ(q₀, a) = q₁", "q₁"],
        ["3", "a", "q₁", "δ(q₁, a) = q₁", "q₁"],
        ["4", "b", "q₁", "δ(q₁, b) = q₂", "q₂ ✓"],
    ]

    colors = [GRAY2] + ["white"] * 4 + [LIGHT_GREEN]
    table = ax2.table(
        cellText=trace_data,
        cellLoc="center",
        loc="center",
        bbox=[0.05, 0.15, 0.9, 0.75],
    )
    table.auto_set_font_size(auto=False)
    table.set_fontsize(FS)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor(GRAY3)
        if row == 0:
            cell.set_facecolor(GRAY2)
            cell.set_text_props(fontweight="bold")
        else:
            cell.set_facecolor(colors[row])
        cell.set_height(0.12)

    ax2.text(
        0.5,
        0.05,
        'Wynik: q₂ ∈ F → "baab" AKCEPTOWANE ✓',
        ha="center",
        va="center",
        fontsize=FS + 1,
        fontweight="bold",
        transform=ax2.transAxes,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_GREEN,
            "edgecolor": LN,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "fa_recognition_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    logger.info("  ✓ fa_recognition_example.png")


# ============================================================
# 2. PDA Recognition Example — PDA for aⁿbⁿ
# ============================================================
def draw_pda_recognition() -> None:
    """PDA state diagram + step-by-step trace with stack."""
    _fig, axes = plt.subplots(
        1,
        2,
        figsize=(11.69, 5.5),
        gridspec_kw={"width_ratios": [1, 1.4]},
    )

    # --- Left: State diagram ---
    ax = axes[0]
    ax.set_xlim(-1, 5.5)
    ax.set_ylim(-2, 3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "PDA — diagram stanów\nL = {aⁿbⁿ | n ≥ 1}",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    state_r = 0.38
    states = {
        "q₀": (0.8, 0.5),
        "q₁": (2.8, 0.5),
        "q₂": (4.8, 0.5),
    }

    draw_state_circle(
        ax,
        states["q₀"],
        state_r,
        "q₀",
        StateStyle(initial=True),
    )
    draw_state_circle(ax, states["q₁"], state_r, "q₁")
    draw_state_circle(
        ax,
        states["q₂"],
        state_r,
        "q₂",
        StateStyle(
            accepting=True, fillcolor=LIGHT_GREEN
        ),
    )

    # q₀ --b,A/ε--> q₁
    draw_curved_arrow(
        ax,
        (states["q₀"][0] + state_r, states["q₀"][1]),
        (states["q₁"][0] - state_r, states["q₁"][1]),
        "b, A → ε\n(pop A)",
        ArrowStyle(
            connectionstyle="arc3,rad=0.0",
            label_offset=(0, 0.4),
        ),
    )
    # q₁ --ε,Z₀/Z₀--> q₂
    draw_curved_arrow(
        ax,
        (states["q₁"][0] + state_r, states["q₁"][1]),
        (states["q₂"][0] - state_r, states["q₂"][1]),
        "ε, Z₀ → Z₀\n(akceptuj)",
        ArrowStyle(
            connectionstyle="arc3,rad=0.0",
            label_offset=(0, 0.45),
        ),
    )
    # q₀ self-loop: a, Z₀/AZ₀ and a, A/AA
    draw_self_loop(
        ax,
        states["q₀"],
        state_r,
        "a, Z₀ → AZ₀\na, A → AA\n(push A)",
        LoopStyle(direction="top"),
    )
    # q₁ self-loop: b, A/ε
    draw_self_loop(
        ax,
        states["q₁"],
        state_r,
        "b, A → ε\n(pop A)",
        LoopStyle(direction="top"),
    )

    # Key explanation
    ax.text(
        0.3,
        -1.3,
        "Notacja: symbol_wejścia, szczyt_stosu"
        " → nowy_szczyt\n"
        "ε = brak symbolu "
        "(przejście spontaniczne lub pusty stos)",
        fontsize=FS_SMALL,
        ha="left",
        va="center",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    # --- Right: Step trace with stack ---
    ax2 = axes[1]
    ax2.axis("off")
    ax2.set_title(
        "Ślad wykonania z wizualizacją stosu"
        ' — wejście: "aabb"',
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    trace_data = [
        [
            "Krok",
            "Czytam",
            "Stan",
            "Stos (szczyt→)",
            "Operacja",
        ],
        ["start", "—", "q₀", "[Z₀]", "—"],
        ["1", "a", "q₀", "[A, Z₀]", "push A"],
        ["2", "a", "q₀", "[A, A, Z₀]", "push A"],
        ["3", "b", "q₁", "[A, Z₀]", "pop A"],
        ["4", "b", "q₁", "[Z₀]", "pop A"],
        ["5", "ε", "q₂", "[Z₀]", "akceptuj!"],
    ]

    colors = [
        GRAY2,
        "white",
        LIGHT_BLUE,
        LIGHT_BLUE,
        LIGHT_YELLOW,
        LIGHT_YELLOW,
        LIGHT_GREEN,
    ]
    table = ax2.table(
        cellText=trace_data,
        cellLoc="center",
        loc="center",
        bbox=[0.02, 0.08, 0.96, 0.82],
    )
    table.auto_set_font_size(auto=False)
    table.set_fontsize(FS)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor(GRAY3)
        if row == 0:
            cell.set_facecolor(GRAY2)
            cell.set_text_props(fontweight="bold")
        else:
            cell.set_facecolor(colors[row])
        cell.set_height(0.11)

    ax2.text(
        0.5,
        0.0,
        "Wynik: q₂ ∈ F, stos=[Z₀]"
        ' → "aabb" AKCEPTOWANE ✓\n'
        'Intuicja: 2x push A (za "aa") '
        '+ 2x pop A (za "bb") = stos pusty = OK',
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
        transform=ax2.transAxes,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_GREEN,
            "edgecolor": LN,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "pda_recognition_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    logger.info("  ✓ pda_recognition_example.png")


# ============================================================
# 3. LBA Recognition Example — LBA for aⁿbⁿcⁿ
# ============================================================
def draw_lba_recognition() -> None:
    """LBA tape visualization showing marking rounds for 'aabbcc'."""
    _fig, ax = plt.subplots(1, 1, figsize=(11.69, 6.5))
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-1, 10.5)
    ax.axis("off")
    ax.set_title(
        "LBA — rozpoznawanie aⁿbⁿcⁿ (n=2)\n"
        "Strategia: w każdej rundzie zaznacz jedno a, b, c",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    cell_w = 0.9
    cell_h = 0.7
    tape_x0 = 1.5
    head_color = "#FFD700"

    def draw_tape(
        tape_y: float,
        cells: list[tuple[str, str]],
        head_pos: int | None,
        label: str,
        *,
        step_label: str = "",
    ) -> None:
        """Draw a tape row with cells, head highlighted."""
        ax.text(
            0.2,
            tape_y + cell_h / 2,
            label,
            ha="right",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )
        for i, (sym, color) in enumerate(cells):
            x = tape_x0 + i * cell_w
            fc = head_color if i == head_pos else color
            rect = mpatches.FancyBboxPatch(
                (x, tape_y),
                cell_w,
                cell_h,
                boxstyle="round,pad=0.03",
                lw=1.2,
                edgecolor=LN,
                facecolor=fc,
            )
            ax.add_patch(rect)
            bold = (
                "bold"
                if sym in ("X", "Y", "Z")
                else "normal"
            )
            ax.text(
                x + cell_w / 2,
                tape_y + cell_h / 2,
                sym,
                ha="center",
                va="center",
                fontsize=FS + 2,
                fontweight=bold,
                family="monospace",
            )
        if head_pos is not None:
            hx = (
                tape_x0
                + head_pos * cell_w
                + cell_w / 2
            )
            ax.annotate(
                "▼",
                xy=(hx, tape_y + cell_h),
                xytext=(hx, tape_y + cell_h + 0.25),
                ha="center",
                va="bottom",
                fontsize=HEAD_MARKER_FONTSIZE,
                color="black",
            )
        if step_label:
            sx = tape_x0 + 6 * cell_w + 0.5
            ax.text(
                sx,
                tape_y + cell_h / 2,
                step_label,
                ha="left",
                va="center",
                fontsize=FS_SMALL,
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "facecolor": GRAY4,
                    "edgecolor": GRAY3,
                },
            )

    white = "white"
    mk = GRAY1  # marked cell color

    # Row 1: Initial tape
    tape_y = 9.0
    draw_tape(
        tape_y,
        [
            ("a", white),
            ("a", white),
            ("b", white),
            ("b", white),
            ("c", white),
            ("c", white),
        ],
        0,
        "Początek",
        step_label=(
            "taśma = [a, a, b, b, c, c], głowica na 0"
        ),
    )

    # Row 2: After marking first 'a'
    tape_y = 7.8
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("a", white),
            ("b", white),
            ("b", white),
            ("c", white),
            ("c", white),
        ],
        1,
        "R1, krok 1",
        step_label="zaznacz a→X, szukaj b",
    )

    # Row 3: After marking first 'b'
    tape_y = 6.6
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("a", white),
            ("Y", mk),
            ("b", white),
            ("c", white),
            ("c", white),
        ],
        3,
        "R1, krok 2",
        step_label="zaznacz b→Y, szukaj c",
    )

    # Row 4: After marking first 'c'
    tape_y = 5.4
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("a", white),
            ("Y", mk),
            ("b", white),
            ("Z", mk),
            ("c", white),
        ],
        0,
        "R1, krok 3",
        step_label="zaznacz c→Z, wróć na początek",
    )

    # Runda 2 header
    tape_y = 4.5
    ax.text(
        tape_x0 + 3 * cell_w,
        tape_y + 0.3,
        "═══ RUNDA 2 ═══",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
        color=LN,
    )

    # Row 5: After marking second 'a'
    tape_y = 3.6
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("X", mk),
            ("Y", mk),
            ("b", white),
            ("Z", mk),
            ("c", white),
        ],
        2,
        "R2, krok 1",
        step_label="pomiń X, zaznacz a→X, szukaj b",
    )

    # Row 6: After marking second 'b'
    tape_y = 2.4
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("X", mk),
            ("Y", mk),
            ("Y", mk),
            ("Z", mk),
            ("c", white),
        ],
        4,
        "R2, krok 2",
        step_label="pomiń Y, zaznacz b→Y, szukaj c",
    )

    # Row 7: After marking second 'c'
    tape_y = 1.2
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("X", mk),
            ("Y", mk),
            ("Y", mk),
            ("Z", mk),
            ("Z", mk),
        ],
        None,
        "R2, krok 3",
        step_label="zaznacz c→Z, wróć na początek",
    )

    # Result
    tape_y = 0.0
    ax.text(
        tape_x0 + 3 * cell_w,
        tape_y + 0.3,
        "Wszystko zaznaczone → q_acc"
        ' → "aabbcc" AKCEPTOWANE ✓',
        ha="center",
        va="center",
        fontsize=FS + 1,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_GREEN,
            "edgecolor": LN,
        },
    )

    # Key
    ax.text(
        tape_x0 + 6 * cell_w + 0.5,
        tape_y + 0.3,
        "Ograniczenie LBA:\n"
        "głowica ≤ 6 komórek\n"
        '(= |w| = |"aabbcc"|)',
        ha="left",
        va="center",
        fontsize=FS_SMALL,
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_YELLOW,
            "edgecolor": GRAY3,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "lba_recognition_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    logger.info("  ✓ lba_recognition_example.png")


# ============================================================
# 4. TM Recognition Example — TM for 0ⁿ1ⁿ
# ============================================================
def draw_tm_recognition() -> None:
    """TM tape visualization for 0ⁿ1ⁿ with infinite tape."""
    _fig, ax = plt.subplots(1, 1, figsize=(11.69, 6.5))
    ax.set_xlim(-0.5, 13)
    ax.set_ylim(-1, 10.5)
    ax.axis("off")
    ax.set_title(
        "TM — rozpoznawanie 0ⁿ1ⁿ (n=2)\n"
        "Strategia: zaznacz jedno 0 i jedno 1"
        " w każdej rundzie",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    cell_w = 0.9
    cell_h = 0.7
    tape_x0 = 1.5
    head_color = "#FFD700"

    def draw_tape(
        tape_y: float,
        cells: list[tuple[str, str]],
        head_pos: int | None,
        label: str,
        *,
        step_label: str = "",
    ) -> None:
        """Draw tape."""
        ax.text(
            0.2,
            tape_y + cell_h / 2,
            label,
            ha="right",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )
        for i, (sym, color) in enumerate(cells):
            x = tape_x0 + i * cell_w
            fc = head_color if i == head_pos else color
            lw = 1.2
            ls = "-"
            if sym == "⊔":
                ls = "--"
            rect = mpatches.FancyBboxPatch(
                (x, tape_y),
                cell_w,
                cell_h,
                boxstyle="round,pad=0.03",
                lw=lw,
                edgecolor=LN,
                facecolor=fc,
                linestyle=ls,
            )
            ax.add_patch(rect)
            bold = (
                "bold" if sym in ("X", "Y") else "normal"
            )
            clr = GRAY3 if sym == "⊔" else LN
            ax.text(
                x + cell_w / 2,
                tape_y + cell_h / 2,
                sym,
                ha="center",
                va="center",
                fontsize=FS + 2,
                fontweight=bold,
                family="monospace",
                color=clr,
            )
        # ∞ arrow
        last_x = tape_x0 + len(cells) * cell_w
        ax.annotate(
            "→ ∞",
            xy=(last_x + 0.3, tape_y + cell_h / 2),
            fontsize=FS,
            ha="left",
            va="center",
            color=GRAY3,
        )
        if head_pos is not None:
            hx = (
                tape_x0
                + head_pos * cell_w
                + cell_w / 2
            )
            ax.annotate(
                "▼",
                xy=(hx, tape_y + cell_h),
                xytext=(hx, tape_y + cell_h + 0.25),
                ha="center",
                va="bottom",
                fontsize=HEAD_MARKER_FONTSIZE,
                color="black",
            )
        if step_label:
            sx = tape_x0 + 8 * cell_w + 0.8
            ax.text(
                sx,
                tape_y + cell_h / 2,
                step_label,
                ha="left",
                va="center",
                fontsize=FS_SMALL,
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "facecolor": GRAY4,
                    "edgecolor": GRAY3,
                },
            )

    white = "white"
    mk = GRAY1
    bl = "#F0F0F0"  # blank cell

    tape_rows = [
        (9.0, [("0", white), ("0", white), ("1", white),
               ("1", white), ("⊔", bl), ("⊔", bl), ("⊔", bl)],
         0, "Początek", "taśma = [0,0,1,1,⊔,⊔,...∞]"),
        (7.8, [("X", mk), ("0", white), ("1", white),
               ("1", white), ("⊔", bl), ("⊔", bl), ("⊔", bl)],
         1, "R1, krok 1", "zaznacz 0→X, idź w prawo"),
        (6.6, [("X", mk), ("0", white), ("Y", mk),
               ("1", white), ("⊔", bl), ("⊔", bl), ("⊔", bl)],
         0, "R1, krok 2", "zaznacz 1→Y, wróć na początek"),
        (4.8, [("X", mk), ("X", mk), ("Y", mk),
               ("1", white), ("⊔", bl), ("⊔", bl), ("⊔", bl)],
         2, "R2, krok 1", "pomiń X, zaznacz 0→X"),
        (3.6, [("X", mk), ("X", mk), ("Y", mk),
               ("Y", mk), ("⊔", bl), ("⊔", bl), ("⊔", bl)],
         0, "R2, krok 2", "pomiń Y, zaznacz 1→Y, wróć"),
        (2.4, [("X", mk), ("X", mk), ("Y", mk),
               ("Y", mk), ("⊔", bl), ("⊔", bl), ("⊔", bl)],
         None, "Sprawdzenie",
         "brak niezaznaczonych → q_acc"),
    ]

    # Runda 2 header
    runda2_y = 5.8
    ax.text(
        tape_x0 + 3.5 * cell_w,
        runda2_y + 0.3,
        "═══ RUNDA 2 ═══",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
    )

    for row_y, cells, head, lbl, step in tape_rows:
        draw_tape(
            row_y, cells, head, lbl, step_label=step
        )

    # Result + TM vs LBA comparison
    tape_y = 0.8
    ax.text(
        tape_x0 + 3.5 * cell_w,
        tape_y + 0.3,
        '"0011" AKCEPTOWANE ✓',
        ha="center",
        va="center",
        fontsize=FS + 1,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_GREEN,
            "edgecolor": LN,
        },
    )

    tape_y = -0.3
    ax.text(
        tape_x0 + 3.5 * cell_w,
        tape_y + 0.3,
        "Różnica TM vs LBA: taśma TM jest "
        "nieskończona (⊔ → ∞)\n"
        "LBA: głowica ograniczona do |w| komórek\n"
        "TM: głowica może wyjść POZA wejście "
        "i pisać na pustych ⊔",
        ha="center",
        va="center",
        fontsize=FS_SMALL,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_YELLOW,
            "edgecolor": GRAY3,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "tm_recognition_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    logger.info("  ✓ tm_recognition_example.png")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    logger.info(
        "Generating automata diagrams for PYTANIE 1..."
    )
    draw_fa_recognition()
    draw_pda_recognition()
    draw_lba_recognition()
    draw_tm_recognition()
    logger.info("All diagrams saved to %s/", OUTPUT_DIR)
