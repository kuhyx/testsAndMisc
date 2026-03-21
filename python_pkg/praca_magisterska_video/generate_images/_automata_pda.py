"""PDA recognition diagram — PDA for a^n b^n."""

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
    LIGHT_BLUE,
    LIGHT_GREEN,
    LIGHT_YELLOW,
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
        StateStyle(accepting=True, fillcolor=LIGHT_GREEN),
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
        'Ślad wykonania z wizualizacją stosu — wejście: "aabb"',
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
