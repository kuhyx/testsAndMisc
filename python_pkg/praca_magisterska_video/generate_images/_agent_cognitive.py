"""Cognitive agent diagrams (Behavior Tree, BDI Model)."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_agent_diagrams import (
    BG,
    DPI,
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


# --- DIAGRAM 3: Behavior Tree Example ---
def draw_behavior_tree() -> None:
    """Draw behavior tree."""
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 4.5), facecolor=BG)
    ax.set_xlim(0, 7.5)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.set_title(
        "Behavior Tree: robot przenosz\u0105cy obiekt (pick-and-place)",
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
        (3.75, 3.8),
        "Przenie\u015b obiekt",
        "seq",
        (1.6, 0.45),
    )

    # Level 2 children
    find = draw_bt_node(
        (1.2, 2.8),
        "Znajd\u017a obiekt",
        "sel",
        (1.3, 0.45),
    )
    nav = draw_bt_node(
        (3.75, 2.8),
        "Jed\u017a do obiektu",
        "act",
        (1.3, 0.45),
    )
    pick = draw_bt_node(
        (6.3, 2.8),
        "Chwy\u0107 i dostarcz",
        "seq",
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
        (0.55, 1.7),
        "Widz\u0119\nobiekt?",
        "cond",
        (0.85, 0.5),
    )
    scan = draw_bt_node(
        (1.85, 1.7),
        "Skanuj\notoczenie",
        "act",
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
            (5.4, 1.7),
            "Chwy\u0107\nobject",
            "act",
            (0.85, 0.5),
        ),
        draw_bt_node(
            (6.5, 1.7),
            "Jed\u017a do\ncelu",
            "act",
            (0.85, 0.5),
        ),
        draw_bt_node(
            (7.2, 1.7),
            "Pu\u015b\u0107",
            "act",
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
        (0.8, leg_y),
        "\u2192 Sequence",
        "seq",
        (1.1, 0.35),
    )
    draw_bt_node(
        (2.3, leg_y),
        "? Selector",
        "sel",
        (1.0, 0.35),
    )
    draw_bt_node((3.6, leg_y), "Akcja", "act", (0.8, 0.35))
    draw_bt_node((4.8, leg_y), "Warunek", "cond", (0.8, 0.35))

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
    path = str(Path(OUTPUT_DIR) / "agent_behavior_tree.png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  \u2713 %s", path)


# --- DIAGRAM 4: BDI Model ---
def draw_bdi_model() -> None:
    """Draw bdi model."""
    fig, ax = plt.subplots(1, 1, figsize=(7, 4), facecolor=BG)
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_title(
        "Model BDI agenta (Beliefs-Desires-Intentions)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    bw = 1.6
    bh = 1.4
    bold8 = BoxStyle(fill=GRAY1, fontsize=8, fontweight="bold")

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
        BoxStyle(fill=GRAY2, fontsize=8, fontweight="bold"),
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
        BoxStyle(fill=GRAY3, fontsize=8, fontweight="bold"),
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
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  \u2713 %s", path)


# --- MAIN ---
