"""FA recognition diagram — DFA for strings ending in 'ab'."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._automata_common import (
    BG,
    DPI,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY2,
    GRAY3,
    GRAY4,
    LIGHT_GREEN,
    LN,
    OUTPUT_DIR,
    ArrowStyle,
    LoopStyle,
    StateStyle,
    draw_curved_arrow,
    draw_self_loop,
    draw_state_circle,
)

logger = logging.getLogger(__name__)


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
        "DFA — diagram stanów\n" 'L = {słowa nad {a,b} kończące się na "ab"}',
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
        StateStyle(accepting=True, fillcolor=LIGHT_GREEN),
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
