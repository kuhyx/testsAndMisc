"""Reactive agent diagrams (See-Think-Act, 3T Architecture)."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_agent_diagrams import (
    BG,
    DPI,
    FS,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    OUTPUT_DIR,
    ArrowCfg,
    BoxStyle,
    draw_arrow,
    draw_box,
)

_logger = logging.getLogger(__name__)


# --- DIAGRAM 1: See-Think-Act Cycle ---
def draw_see_think_act() -> None:
    """Draw see think act."""
    fig, ax = plt.subplots(1, 1, figsize=(7, 4.5), facecolor=BG)
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.set_title(
        "Cykl agenta upostaciowionego:" " Percepcja \u2192 Deliberacja \u2192 Akcja",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Environment box (large background)
    env_rect = FancyBboxPatch(
        (0.2, 0.2),
        6.6,
        1.0,
        boxstyle="round,pad=0.08",
        lw=1.5,
        edgecolor=LN,
        facecolor=GRAY1,
        linestyle="--",
    )
    ax.add_patch(env_rect)
    ax.text(
        3.5,
        0.7,
        "\u015aRODOWISKO FIZYCZNE\n" "(przeszkody, obiekty, ludzie)",
        ha="center",
        va="center",
        fontsize=FS,
        fontstyle="italic",
    )

    # Agent body (large rounded box)
    agent_rect = FancyBboxPatch(
        (0.5, 1.5),
        6.0,
        2.6,
        boxstyle="round,pad=0.1",
        lw=2.0,
        edgecolor=LN,
        facecolor=GRAY4,
    )
    ax.add_patch(agent_rect)
    ax.text(
        3.5,
        3.85,
        "AGENT UPOSTACIOWIONY (robot)",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
    )

    # Three main phases
    bw = 1.4
    bh = 0.7
    by = 2.2
    bold_fs8 = BoxStyle(fill=GRAY2, fontsize=8, fontweight="bold")

    # SEE
    draw_box(
        ax,
        (0.8, by),
        (bw, bh),
        "SEE\n(Percepcja)",
        bold_fs8,
    )
    ax.text(
        1.5,
        by - 0.2,
        "kamery, LIDAR\nczujniki dotyku",
        ha="center",
        va="top",
        fontsize=6,
        fontstyle="italic",
    )

    # THINK
    draw_box(
        ax,
        (2.8, by),
        (bw, bh),
        "THINK\n(Deliberacja)",
        BoxStyle(fill=GRAY3, fontsize=8, fontweight="bold"),
    )
    ax.text(
        3.5,
        by - 0.2,
        "planowanie trasy\nmodel BDI",
        ha="center",
        va="top",
        fontsize=6,
        fontstyle="italic",
    )

    # ACT
    draw_box(
        ax,
        (4.8, by),
        (bw, bh),
        "ACT\n(Akcja)",
        bold_fs8,
    )
    ax.text(
        5.5,
        by - 0.2,
        "silniki, chwytaki\nkomendy PWM",
        ha="center",
        va="top",
        fontsize=6,
        fontstyle="italic",
    )

    # Arrows between phases
    draw_arrow(
        ax,
        (0.8 + bw, by + bh / 2),
        (2.8, by + bh / 2),
        ArrowCfg(lw=1.5, label="dane sensoryczne"),
    )
    draw_arrow(
        ax,
        (2.8 + bw, by + bh / 2),
        (4.8, by + bh / 2),
        ArrowCfg(lw=1.5, label="komendy steruj\u0105ce"),
    )

    # Arrows to/from environment
    draw_arrow(
        ax,
        (1.5, 1.2),
        (1.5, by),
        ArrowCfg(
            lw=1.3,
            label="odczyt",
            label_offset=0.08,
        ),
    )
    draw_arrow(
        ax,
        (5.5, by),
        (5.5, 1.2),
        ArrowCfg(
            lw=1.3,
            label="dzia\u0142anie",
            label_offset=0.08,
        ),
    )

    # Feedback loop arrow
    ax.annotate(
        "",
        xy=(1.5, 1.15),
        xytext=(5.5, 1.15),
        arrowprops={
            "arrowstyle": "->",
            "color": "#555555",
            "lw": 1.0,
            "linestyle": "dashed",
            "connectionstyle": "arc3,rad=-0.15",
        },
    )
    ax.text(
        3.5,
        0.35,
        "\u2190 sprz\u0119\u017cenie zwrotne"
        " (efekt akcji zmienia \u015brodowisko) \u2192",
        ha="center",
        va="center",
        fontsize=6,
        color="#555555",
    )

    fig.tight_layout()
    path = str(Path(OUTPUT_DIR) / "agent_see_think_act.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  \u2713 %s", path)


# --- DIAGRAM 2: 3T Architecture ---
def draw_3t_architecture() -> None:
    """Draw 3t architecture."""
    fig, ax = plt.subplots(1, 1, figsize=(7, 5.5), facecolor=BG)
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 5.5)
    ax.axis("off")
    ax.set_title(
        "Architektura 3T sterownika robota" " (3-Layer Architecture)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    layers = [
        {
            "y": 4.0,
            "name": "WARSTWA 3: PLANNER\n(Deliberacja)",
            "time": "sekundy \u2013 minuty",
            "fill": GRAY1,
            "example": (
                'Cel: "Jed\u017a do kuchni po kubek"\n'
                "Planowanie trasy A \u2192 B \u2192 C"
            ),
        },
        {
            "y": 2.6,
            "name": "WARSTWA 2: SEQUENCER\n(Wykonawca)",
            "time": "100 ms \u2013 sekundy",
            "fill": GRAY2,
            "example": (
                "Sekwencja: Jed\u017a do drzwi \u2192\n"
                "Otw\u00f3rz \u2192 Jed\u017a do blatu"
                " \u2192 Chwy\u0107"
            ),
        },
        {
            "y": 1.2,
            "name": "WARSTWA 1: CONTROLLER\n(Reaktywny)",
            "time": "milisekundy",
            "fill": GRAY3,
            "example": (
                "PID: utrzymaj pr\u0119dko\u015b\u0107"
                " 0.5 m/s\n"
                "Unikaj kolizji (emergency stop)"
            ),
        },
    ]

    bw = 4.0
    bh = 0.85

    for layer in layers:
        y = layer["y"]
        draw_box(
            ax,
            (0.3, y),
            (bw, bh),
            layer["name"],
            BoxStyle(
                fill=layer["fill"],
                fontsize=8,
                fontweight="bold",
            ),
        )

        ax.text(
            0.15,
            y + bh / 2,
            layer["time"],
            ha="right",
            va="center",
            fontsize=6,
            fontstyle="italic",
            rotation=0,
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": "white",
                "edgecolor": LN,
                "lw": 0.5,
            },
        )

        draw_box(
            ax,
            (4.5, y),
            (2.3, bh),
            layer["example"],
            BoxStyle(fontsize=6.5),
        )

    # Arrows between layers
    for i in range(len(layers) - 1):
        y_top = layers[i]["y"]
        y_bot = layers[i + 1]["y"] + 0.85
        draw_arrow(
            ax,
            (1.8, y_top),
            (1.8, y_bot),
            ArrowCfg(
                lw=1.3,
                label="polecenia \u2193",
                label_offset=0.02,
            ),
        )
        draw_arrow(
            ax,
            (2.8, y_bot),
            (2.8, y_top),
            ArrowCfg(
                lw=1.0,
                color="#666666",
                label="\u2191 status",
                label_offset=0.02,
            ),
        )

    # Environment at bottom
    env_rect = FancyBboxPatch(
        (0.3, 0.3),
        bw,
        0.6,
        boxstyle="round,pad=0.05",
        lw=1.5,
        edgecolor=LN,
        facecolor=GRAY4,
        linestyle="--",
    )
    ax.add_patch(env_rect)
    ax.text(
        0.3 + bw / 2,
        0.6,
        "SPRZ\u0118T: silniki, czujniki, efektory",
        ha="center",
        va="center",
        fontsize=7,
        fontstyle="italic",
    )

    draw_arrow(ax, (2.3, 1.2), (2.3, 0.9), ArrowCfg(lw=1.3))

    # Abstraction label on the right
    ax.annotate(
        "",
        xy=(6.9, 4.8),
        xytext=(6.9, 0.5),
        arrowprops={
            "arrowstyle": "<->",
            "color": "#888888",
            "lw": 1.0,
        },
    )
    ax.text(
        6.95,
        2.65,
        "abstrakcja",
        ha="left",
        va="center",
        fontsize=7,
        rotation=90,
        color="#888888",
    )

    fig.tight_layout()
    path = str(Path(OUTPUT_DIR) / "agent_3t_architecture.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  \u2713 %s", path)
