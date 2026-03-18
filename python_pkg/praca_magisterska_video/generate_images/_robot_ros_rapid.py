"""ROS architecture and RAPID structure diagrams."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_robot_lang_diagrams import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OUTPUT_DIR,
    WHITE,
    draw_arrow,
    draw_box,
)

_logger = logging.getLogger(__name__)


# ============================================================
# 5. ROS Architecture (pub/sub)
# ============================================================
def draw_ros_architecture() -> None:
    """Draw ros architecture."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "ROS — architektura publish/subscribe",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Nodes
    nodes = [
        (1.0, 4.5, "Czujnik\n(LiDAR)", GRAY1),
        (1.0, 2.5, "Kamera\n(RGB-D)", GRAY1),
        (4.0, 4.5, "Lokalizacja\n(SLAM)", GRAY4),
        (4.0, 2.5, "Percepcja\n(detekcja)", GRAY4),
        (7.0, 3.5, "Planowanie\nruchu (MoveIt)", GRAY2),
        (7.0, 1.0, "Sterownik\nsilników", GRAY3),
    ]

    for x, y, txt, fill in nodes:
        draw_box(ax, x, y, 2.2, 1.0, txt, fill=fill, fontsize=7, fontweight="bold")

    # Topics (arrows with labels)
    topics = [
        # Fields: from_x  from_y  to_x  to_y  label
        (3.2, 5.0, 4.0, 5.0, "/scan"),
        (3.2, 3.0, 4.0, 3.0, "/image"),
        (6.2, 5.0, 7.0, 4.3, "/pose"),
        (6.2, 3.0, 7.0, 3.8, "/objects"),
        (8.0, 3.5, 8.0, 2.0, "/cmd_vel"),
    ]

    for x1, y1, x2, y2, label in topics:
        draw_arrow(ax, x1, y1, x2, y2, lw=1.5)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx,
            my + 0.2,
            label,
            ha="center",
            va="bottom",
            fontsize=6,
            fontweight="bold",
            style="italic",
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": WHITE,
                "edgecolor": GRAY5,
                "lw": 0.5,
            },
        )

    # ROS Master / roscore
    draw_box(
        ax,
        3.5,
        0.3,
        3.0,
        0.8,
        "ROS Master (roscore)\nRejestr węzłów i tematów",
        fill=GRAY2,
        fontsize=7,
        fontweight="bold",
    )

    # Dashed lines to master
    for x, y, _, _ in nodes[:4]:
        ax.plot([x + 1.1, 5.0], [y, 1.1], "k:", lw=0.5, alpha=0.4)

    # Legend
    ax.text(
        0.3,
        0.8,
        "Węzeł (Node) = proces\n"
        "Temat (Topic) = kanał pub/sub\n"
        "Wiadomość = typowany komunikat",
        ha="left",
        va="center",
        fontsize=6,
        bbox={"boxstyle": "round", "facecolor": GRAY4, "edgecolor": LN, "lw": 0.8},
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "robot_ros_architecture.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)
    _logger.info("Generated robot_ros_architecture.png")


# ============================================================
# 6. RAPID program structure example
# ============================================================
def draw_rapid_structure() -> None:
    """Draw rapid structure."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title(
        "Struktura programu RAPID (ABB) — przykład pick & place",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Program structure blocks

    # Simplified: just draw code blocks
    code_sections = [
        (
            "Deklaracje danych (stałe, zmienne)",
            GRAY4,
            [
                "CONST robtarget pHome := [[500,0,600],[1,0,0,0],...];",
                "CONST robtarget pPick := [[400,200,100],[1,0,0,0],...];",
                "CONST robtarget pPlace := [[400,-200,100],[1,0,0,0],...];",
                "VAR num nCycles := 0;",
                "PERS tooldata tGripper := [...];",
            ],
        ),
        (
            "Procedura główna: main()",
            GRAY1,
            [
                "PROC main()",
                "    MoveJ pHome, v1000, z50, tGripper;",
                "    WHILE TRUE DO",
                "        PickPart;",
                "        PlacePart;",
                "        Incr nCycles;",
                "    ENDWHILE",
                "ENDPROC",
            ],
        ),
        (
            "Podprocedura: PickPart()",
            GRAY1,
            [
                "PROC PickPart()",
                "    MoveL Offs(pPick,0,0,50), v500, z10, tGripper;",
                "    MoveL pPick, v100, fine, tGripper;",
                "    SetDO doGripper, 1;    ! zamknij chwytak",
                "    WaitTime 0.5;",
                "    MoveL Offs(pPick,0,0,50), v500, z10, tGripper;",
                "ENDPROC",
            ],
        ),
    ]

    y_cur = 7.2
    for title, fill, lines in code_sections:
        0.25 * len(lines) + 0.5
        # Title bar
        draw_box(
            ax,
            0.5,
            y_cur - 0.35,
            9.0,
            0.35,
            title,
            fill=fill,
            fontsize=7,
            fontweight="bold",
            rounded=False,
        )
        y_cur -= 0.35

        # Code lines
        for _i, line in enumerate(lines):
            y_cur -= 0.25
            ax.text(
                0.7,
                y_cur + 0.12,
                line,
                fontsize=5.5,
                fontfamily="monospace",
                va="center",
            )

        # Border around code
        code_h = 0.25 * len(lines)
        rect = mpatches.Rectangle(
            (0.5, y_cur - 0.05),
            9.0,
            code_h + 0.15,
            lw=0.8,
            edgecolor=GRAY5,
            facecolor=WHITE,
            zorder=-1,
        )
        ax.add_patch(rect)

        y_cur -= 0.3

    # Annotations on right
    annotations = [
        (
            6.5,
            "robtarget = pozycja\nkartezjańska + orientacja\n+ konfiguracja ramienia",
        ),
        (
            4.5,
            "v500 = prędkość 500 mm/s\n"
            "z10 = strefa zbliżenia 10mm\n"
            "fine = dokładne dojście",
        ),
        (2.5, "SetDO = Digital Output\nSterowanie I/O\n(chwytak, zawory)"),
    ]

    for yy, txt in annotations:
        ax.text(
            9.8,
            yy,
            txt,
            fontsize=5.5,
            ha="left",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": GRAY4,
                "edgecolor": GRAY5,
                "lw": 0.5,
            },
        )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "robot_rapid_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)
    _logger.info("Generated robot_rapid_example.png")


# ============================================================
# Main
# ============================================================
