#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 15: Agent upostaciowiony w robotyce.

Diagrams:
  1. See-Think-Act cycle of an embodied agent
  2. 3T Architecture (Planner / Sequencer / Controller)
  3. Behavior Tree example (robot pick-and-place)
  4. BDI model flow

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
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"


@dataclass(frozen=True)
class BoxStyle:
    """Optional styling for boxes."""

    fill: str = "white"
    lw: float = 1.2
    fontsize: float = FS
    fontweight: str = "normal"
    ha: str = "center"
    va: str = "center"
    rounded: bool = True


@dataclass(frozen=True)
class ArrowCfg:
    """Optional config for arrows."""

    lw: float = 1.2
    style: str = "->"
    color: str = LN
    label: str = ""
    label_offset: float = 0.12


@dataclass(frozen=True)
class DashedArrowCfg:
    """Optional config for dashed arrows."""

    lw: float = 1.0
    color: str = LN
    label: str = ""
    label_offset: float = 0.12


def draw_box(
    ax: Axes,
    pos: tuple[float, float],
    size: tuple[float, float],
    text: str,
    style: BoxStyle | None = None,
) -> None:
    """Draw box."""
    s = style or BoxStyle()
    x, y = pos
    w, h = size
    if s.rounded:
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05",
            lw=s.lw,
            edgecolor=LN,
            facecolor=s.fill,
        )
    else:
        rect = mpatches.Rectangle(
            (x, y),
            w,
            h,
            lw=s.lw,
            edgecolor=LN,
            facecolor=s.fill,
        )
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha=s.ha,
        va=s.va,
        fontsize=s.fontsize,
        fontweight=s.fontweight,
        wrap=True,
    )


def draw_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    cfg: ArrowCfg | None = None,
) -> None:
    """Draw arrow."""
    c = cfg or ArrowCfg()
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": c.style,
            "color": c.color,
            "lw": c.lw,
        },
    )
    if c.label:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2 + c.label_offset
        ax.text(
            mx,
            my,
            c.label,
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=c.color,
        )


def draw_dashed_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    cfg: DashedArrowCfg | None = None,
) -> None:
    """Draw dashed arrow."""
    c = cfg or DashedArrowCfg()
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "->",
            "color": c.color,
            "lw": c.lw,
            "linestyle": "dashed",
        },
    )
    if c.label:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2 + c.label_offset
        ax.text(
            mx,
            my,
            c.label,
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=c.color,
        )


# --- DIAGRAM 1: See-Think-Act Cycle ---
def draw_see_think_act() -> None:
    """Draw see think act."""
    fig, ax = plt.subplots(
        1, 1, figsize=(7, 4.5), facecolor=BG
    )
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.set_title(
        "Cykl agenta upostaciowionego:"
        " Percepcja \u2192 Deliberacja \u2192 Akcja",
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
        "\u015aRODOWISKO FIZYCZNE\n"
        "(przeszkody, obiekty, ludzie)",
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
    bold_fs8 = BoxStyle(
        fill=GRAY2, fontsize=8, fontweight="bold"
    )

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
        BoxStyle(
            fill=GRAY3, fontsize=8, fontweight="bold"
        ),
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
        ArrowCfg(
            lw=1.5, label="komendy steruj\u0105ce"
        ),
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
    path = str(
        Path(OUTPUT_DIR) / "agent_see_think_act.png"
    )
    fig.savefig(
        path, dpi=DPI, bbox_inches="tight", facecolor=BG
    )
    plt.close(fig)
    logger.info("  \u2713 %s", path)


# --- DIAGRAM 2: 3T Architecture ---
def draw_3t_architecture() -> None:
    """Draw 3t architecture."""
    fig, ax = plt.subplots(
        1, 1, figsize=(7, 5.5), facecolor=BG
    )
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 5.5)
    ax.axis("off")
    ax.set_title(
        "Architektura 3T sterownika robota"
        " (3-Layer Architecture)",
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

    draw_arrow(
        ax, (2.3, 1.2), (2.3, 0.9), ArrowCfg(lw=1.3)
    )

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
    path = str(
        Path(OUTPUT_DIR) / "agent_3t_architecture.png"
    )
    fig.savefig(
        path, dpi=DPI, bbox_inches="tight", facecolor=BG
    )
    plt.close(fig)
    logger.info("  \u2713 %s", path)


# --- DIAGRAM 3: Behavior Tree Example ---
def draw_behavior_tree() -> None:
    """Draw behavior tree."""
    fig, ax = plt.subplots(
        1, 1, figsize=(7.5, 4.5), facecolor=BG
    )
    ax.set_xlim(0, 7.5)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.set_title(
        "Behavior Tree: robot przenosz\u0105cy"
        " obiekt (pick-and-place)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    def draw_bt_node(
        pos: tuple[float, float],
        text: str,
        ntype: str = "act",
        size: tuple[float, float] = (1.0, 0.45),
    ) -> tuple[float, float]:
        """Draw a behavior tree node."""
        x, y = pos
        w, h = size
        if ntype == "seq":
            rect = FancyBboxPatch(
                (x - w / 2, y - h / 2),
                w,
                h,
                boxstyle="round,pad=0.06",
                lw=1.5,
                edgecolor=LN,
                facecolor=GRAY2,
            )
            ax.add_patch(rect)
            ax.text(
                x,
                y,
                f"\u2192 {text}",
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
            )
        elif ntype == "sel":
            rect = FancyBboxPatch(
                (x - w / 2, y - h / 2),
                w,
                h,
                boxstyle="round,pad=0.06",
                lw=1.5,
                edgecolor=LN,
                facecolor=GRAY3,
            )
            ax.add_patch(rect)
            ax.text(
                x,
                y,
                f"? {text}",
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
            )
        elif ntype == "cond":
            rect = FancyBboxPatch(
                (x - w / 2, y - h / 2),
                w,
                h,
                boxstyle="round,pad=0.06",
                lw=1.0,
                edgecolor=LN,
                facecolor="white",
                linestyle="--",
            )
            ax.add_patch(rect)
            ax.text(
                x,
                y,
                text,
                ha="center",
                va="center",
                fontsize=6.5,
                fontstyle="italic",
            )
        else:  # action
            rect = FancyBboxPatch(
                (x - w / 2, y - h / 2),
                w,
                h,
                boxstyle="round,pad=0.06",
                lw=1.0,
                edgecolor=LN,
                facecolor=GRAY1,
            )
            ax.add_patch(rect)
            ax.text(
                x,
                y,
                text,
                ha="center",
                va="center",
                fontsize=6.5,
            )
        return x, y

    # Root: Sequence "Przenies obiekt"
    root = draw_bt_node(
        (3.75, 3.8), "Przenie\u015b obiekt", "seq",
        (1.6, 0.45),
    )

    # Level 2 children
    find = draw_bt_node(
        (1.2, 2.8), "Znajd\u017a obiekt", "sel",
        (1.3, 0.45),
    )
    nav = draw_bt_node(
        (3.75, 2.8), "Jed\u017a do obiektu", "act",
        (1.3, 0.45),
    )
    pick = draw_bt_node(
        (6.3, 2.8), "Chwy\u0107 i dostarcz", "seq",
        (1.4, 0.45),
    )

    # Arrows from root
    arrow_thin = ArrowCfg(lw=1.0)
    for child in (find, nav, pick):
        draw_arrow(
            ax,
            (root[0], root[1] - 0.225),
            (child[0], child[1] + 0.225),
            arrow_thin,
        )

    # Level 3: children of "Znajdz obiekt"
    arrow_08 = ArrowCfg(lw=0.8)
    vis = draw_bt_node(
        (0.55, 1.7), "Widz\u0119\nobiekt?", "cond",
        (0.85, 0.5),
    )
    scan = draw_bt_node(
        (1.85, 1.7), "Skanuj\notoczenie", "act",
        (0.85, 0.5),
    )
    for child in (vis, scan):
        draw_arrow(
            ax,
            (find[0], find[1] - 0.225),
            (child[0], child[1] + 0.25),
            arrow_08,
        )

    # Level 3: children of "Chwyt i dostarcz"
    pick_children = [
        draw_bt_node(
            (5.4, 1.7), "Chwy\u0107\nobject", "act",
            (0.85, 0.5),
        ),
        draw_bt_node(
            (6.5, 1.7), "Jed\u017a do\ncelu", "act",
            (0.85, 0.5),
        ),
        draw_bt_node(
            (7.2, 1.7), "Pu\u015b\u0107", "act",
            (0.55, 0.5),
        ),
    ]
    for child in pick_children:
        draw_arrow(
            ax,
            (pick[0], pick[1] - 0.225),
            (child[0], child[1] + 0.25),
            arrow_08,
        )

    # Legend
    leg_y = 0.5
    draw_bt_node(
        (0.8, leg_y), "\u2192 Sequence", "seq",
        (1.1, 0.35),
    )
    draw_bt_node(
        (2.3, leg_y), "? Selector", "sel",
        (1.0, 0.35),
    )
    draw_bt_node(
        (3.6, leg_y), "Akcja", "act", (0.8, 0.35)
    )
    draw_bt_node(
        (4.8, leg_y), "Warunek", "cond", (0.8, 0.35)
    )

    ax.text(
        0.3,
        leg_y,
        "Legenda:",
        ha="left",
        va="center",
        fontsize=6.5,
        fontweight="bold",
    )

    # Execution note
    ax.text(
        3.75,
        0.05,
        "Wykonanie: od lewej do prawej."
        " Sequence (\u2192) = wszystkie po kolei."
        " Selector (?) = pierwszy sukces.",
        ha="center",
        va="center",
        fontsize=6,
        fontstyle="italic",
        color="#555555",
    )

    fig.tight_layout()
    path = str(
        Path(OUTPUT_DIR) / "agent_behavior_tree.png"
    )
    fig.savefig(
        path, dpi=DPI, bbox_inches="tight", facecolor=BG
    )
    plt.close(fig)
    logger.info("  \u2713 %s", path)


# --- DIAGRAM 4: BDI Model ---
def draw_bdi_model() -> None:
    """Draw bdi model."""
    fig, ax = plt.subplots(
        1, 1, figsize=(7, 4), facecolor=BG
    )
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_title(
        "Model BDI agenta"
        " (Beliefs-Desires-Intentions)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    bw = 1.6
    bh = 1.4
    bold8 = BoxStyle(
        fill=GRAY1, fontsize=8, fontweight="bold"
    )

    # BELIEFS box
    draw_box(ax, (0.3, 1.3), (bw, bh), "", bold8)
    ax.text(
        0.3 + bw / 2,
        1.3 + bh - 0.15,
        "BELIEFS",
        ha="center",
        va="top",
        fontsize=9,
        fontweight="bold",
    )
    ax.text(
        0.3 + bw / 2,
        1.3 + bh / 2 - 0.1,
        "(wiedza o \u015bwiecie)\n\n"
        "\u2022 mapa pokoju\n"
        "\u2022 pozycja robota\n"
        "\u2022 drzwi zamkni\u0119te\n"
        "\u2022 bateria: 45%",
        ha="center",
        va="center",
        fontsize=6.5,
    )

    # DESIRES box
    draw_box(
        ax,
        (2.7, 1.3),
        (bw, bh),
        "",
        BoxStyle(
            fill=GRAY2, fontsize=8, fontweight="bold"
        ),
    )
    ax.text(
        2.7 + bw / 2,
        1.3 + bh - 0.15,
        "DESIRES",
        ha="center",
        va="top",
        fontsize=9,
        fontweight="bold",
    )
    ax.text(
        2.7 + bw / 2,
        1.3 + bh / 2 - 0.1,
        "(cele agenta)\n\n"
        "\u2022 dostarczy\u0107 paczk\u0119\n"
        "  do pokoju 5\n"
        "\u2022 na\u0142adowa\u0107 bateri\u0119\n"
        "\u2022 unika\u0107 kolizji",
        ha="center",
        va="center",
        fontsize=6.5,
    )

    # INTENTIONS box
    draw_box(
        ax,
        (5.1, 1.3),
        (bw, bh),
        "",
        BoxStyle(
            fill=GRAY3, fontsize=8, fontweight="bold"
        ),
    )
    ax.text(
        5.1 + bw / 2,
        1.3 + bh - 0.15,
        "INTENTIONS",
        ha="center",
        va="top",
        fontsize=9,
        fontweight="bold",
    )
    ax.text(
        5.1 + bw / 2,
        1.3 + bh / 2 - 0.1,
        "(aktualny plan)\n\n"
        "\u2192 jed\u017a do drzwi\n"
        "  bocznych\n"
        "\u2192 otw\u00f3rz drzwi\n"
        "\u2192 wjed\u017a do pokoju 5",
        ha="center",
        va="center",
        fontsize=6.5,
    )

    # Arrows
    draw_arrow(
        ax,
        (0.3 + bw, 1.3 + bh / 2 + 0.15),
        (2.7, 1.3 + bh / 2 + 0.15),
        ArrowCfg(
            lw=1.3,
            label="informuje",
            label_offset=0.08,
        ),
    )
    draw_arrow(
        ax,
        (2.7 + bw, 1.3 + bh / 2 + 0.15),
        (5.1, 1.3 + bh / 2 + 0.15),
        ArrowCfg(
            lw=1.3,
            label="filtruje \u2192 wybiera",
            label_offset=0.08,
        ),
    )

    # Feedback: intentions back to beliefs
    ax.annotate(
        "",
        xy=(0.3 + bw / 2, 1.3),
        xytext=(5.1 + bw / 2, 1.3),
        arrowprops={
            "arrowstyle": "->",
            "color": "#666666",
            "lw": 1.0,
            "linestyle": "dashed",
            "connectionstyle": "arc3,rad=0.3",
        },
    )
    ax.text(
        3.5,
        0.75,
        "aktualizacja wiedzy po wykonaniu akcji",
        ha="center",
        va="center",
        fontsize=6,
        fontstyle="italic",
        color="#666666",
    )

    # Sensor input arrow
    draw_arrow(
        ax,
        (0.3 + bw / 2, 3.5),
        (0.3 + bw / 2, 1.3 + bh),
        ArrowCfg(
            lw=1.3,
            label="percepcja (sensory)",
            label_offset=0.05,
        ),
    )
    ax.text(
        0.3 + bw / 2,
        3.55,
        "\u015aRODOWISKO",
        ha="center",
        va="bottom",
        fontsize=7,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.8,
        },
    )

    # Action output arrow
    draw_arrow(
        ax,
        (5.1 + bw / 2, 1.3 + bh),
        (5.1 + bw / 2, 3.5),
        ArrowCfg(
            lw=1.3,
            label="akcja (efektory)",
            label_offset=0.05,
        ),
    )
    ax.text(
        5.1 + bw / 2,
        3.55,
        "EFEKTORY",
        ha="center",
        va="bottom",
        fontsize=7,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.8,
        },
    )

    fig.tight_layout()
    path = str(Path(OUTPUT_DIR) / "agent_bdi_model.png")
    fig.savefig(
        path, dpi=DPI, bbox_inches="tight", facecolor=BG
    )
    plt.close(fig)
    logger.info("  \u2713 %s", path)


# --- MAIN ---
if __name__ == "__main__":
    logger.info("Generating PYTANIE 15 diagrams...")
    draw_see_think_act()
    draw_3t_architecture()
    draw_behavior_tree()
    draw_bdi_model()
    logger.info("Done! All diagrams saved to %s", OUTPUT_DIR)
