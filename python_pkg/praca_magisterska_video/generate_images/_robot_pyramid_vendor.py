"""Robot language diagrams - TRMS pyramid and vendor comparison."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_robot_lang_diagrams import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    OUTPUT_DIR,
    WHITE,
    draw_box,
)

_logger = logging.getLogger(__name__)

# ============================================================
# 1. T-R-M-S Abstraction Pyramid
# ============================================================
def draw_trms_pyramid() -> None:
    """Draw trms pyramid."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Poziomy abstrakcji języków programowania robotów (T-R-M-S)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Pyramid layers (bottom to top)
    layers = [
        # Fields: y  left_x  right_x  label  sublabel  fill  examples  timing
        (
            0.5,
            1.0,
            9.0,
            "SERVO-LEVEL",
            "Sterowanie silnikami",
            GRAY3,
            "C/C++, FPGA, VHDL\nPID, PWM",
            "~1 ms",
        ),
        (
            2.0,
            1.8,
            8.2,
            "MOTION-LEVEL",
            "Planowanie trajektorii",
            GRAY2,
            "MoveIt, OMPL\nIK, collision avoidance",
            "~20 ms",
        ),
        (
            3.5,
            2.6,
            7.4,
            "ROBOT-LEVEL",
            "Komendy ruchu",
            GRAY1,
            "RAPID, KRL, Karel\nPDL2, URScript, ROS",
            "~100 ms",
        ),
        (
            5.0,
            3.4,
            6.6,
            "TASK-LEVEL",
            "Opis celu",
            GRAY4,
            "PDDL, BT, STRIPS\nplanowanie AI",
            "~sekundy",
        ),
    ]

    h = 1.3
    for y, lx, rx, label, sublabel, fill, examples, timing in layers:
        rx - lx
        # Draw trapezoid
        trap = plt.Polygon(
            [(lx, y), (rx, y), (rx - 0.4, y + h), (lx + 0.4, y + h)],
            closed=True,
            facecolor=fill,
            edgecolor=LN,
            lw=1.5,
        )
        ax.add_patch(trap)

        # Label
        ax.text(
            (lx + rx) / 2,
            y + h * 0.65,
            label,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
        )
        ax.text(
            (lx + rx) / 2,
            y + h * 0.35,
            sublabel,
            ha="center",
            va="center",
            fontsize=7,
            style="italic",
        )

        # Examples - right side
        ax.text(
            rx + 0.2,
            y + h * 0.5,
            examples,
            ha="left",
            va="center",
            fontsize=6.5,
            color="#333333",
        )

        # Timing - left side
        ax.text(
            lx - 0.2,
            y + h * 0.5,
            timing,
            ha="right",
            va="center",
            fontsize=7,
            fontweight="bold",
            color="#333333",
        )

    # Arrow on left
    ax.annotate(
        "",
        xy=(0.5, 6.2),
        xytext=(0.5, 0.8),
        arrowprops={"arrowstyle": "->", "color": "black", "lw": 2},
    )
    ax.text(
        0.5,
        3.5,
        "Abstrakcja\nrośnie",
        ha="center",
        va="center",
        fontsize=7,
        rotation=90,
        fontweight="bold",
    )

    # Arrow on right side for timing
    ax.annotate(
        "",
        xy=(9.7, 0.8),
        xytext=(9.7, 6.2),
        arrowprops={"arrowstyle": "->", "color": "black", "lw": 2},
    )
    ax.text(
        9.7,
        3.5,
        "Szybkość\nreakcji",
        ha="center",
        va="center",
        fontsize=7,
        rotation=270,
        fontweight="bold",
    )

    # Mnemonic at bottom
    ax.text(
        5.0,
        0.0,
        'Mnemonik: „Tomek Robi Mechaniczne Serwa" (T→R→M→S, od góry do dołu)',
        ha="center",
        va="center",
        fontsize=7,
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.8,
        },
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "robot_trms_pyramid.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)
    _logger.info("Generated robot_trms_pyramid.png")


# ============================================================
# 2. Vendor Languages Comparison
# ============================================================
def draw_vendor_comparison() -> None:
    """Draw vendor comparison."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.5)
    ax.axis("off")
    ax.set_title(
        "Języki producentów robotów — porównanie",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Table headers
    headers = [
        "Cecha",
        "RAPID\n(ABB)",
        "KRL\n(KUKA)",
        "Karel\n(FANUC)",
        "PDL2\n(Comau)",
        "URScript\n(UR)",
    ]
    col_widths = [1.8, 1.6, 1.6, 1.6, 1.6, 1.6]
    col_x = [0.1]
    for w in col_widths[:-1]:
        col_x.append(col_x[-1] + w)

    row_h = 0.7
    header_y = 6.3
    rows = [
        [
            "Składnia",
            "typ własny\nstrukturalna",
            "Pascal-like\nstrukturalna",
            "Pascal-like\nstrukturalna",
            "proceduralna\nC-like",
            "Python-like\nskryptowy",
        ],
        [
            "Ruch liniowy",
            "MoveL",
            "LIN",
            "MOVE TO\nw/LINEAR",
            "MOVE\nLINEAR TO",
            "movel()",
        ],
        ["Ruch joint", "MoveJ", "PTP", "MOVE TO", "MOVE TO", "movej()"],
        [
            "Ruch kołowy",
            "MoveC",
            "CIRC",
            "(brak\nwbudow.)",
            "MOVE\nCIRCULAR",
            "movec()",
        ],
        [
            "I/O",
            "SetDO/\nWaitDI",
            "OUT/IN",
            "DOUT/DIN",
            "OUT/IN",
            "set_digital\n_out()",
        ],
        [
            "Zmienne",
            "num, robtarget\nstring, bool",
            "INT, REAL\nPOS, E6POS",
            "INTEGER\nPOSITION",
            "INTEGER\nPOSITION",
            "int, float\npose",
        ],
        [
            "Symulator",
            "RobotStudio",
            "KUKA.Sim",
            "ROBOGUIDE",
            "RoboSim",
            "URSim\n(darmowy)",
        ],
    ]

    # Draw header row
    for j, (hdr, w) in enumerate(zip(headers, col_widths, strict=False)):
        x = col_x[j]
        fill = GRAY2 if j == 0 else GRAY1
        draw_box(
            ax,
            x,
            header_y,
            w - 0.05,
            row_h,
            hdr,
            fill=fill,
            fontsize=7,
            fontweight="bold",
            rounded=False,
        )

    # Draw data rows
    for i, row in enumerate(rows):
        y = header_y - (i + 1) * row_h
        for j, (cell, w) in enumerate(zip(row, col_widths, strict=False)):
            x = col_x[j]
            fill = GRAY4 if j == 0 else (WHITE if i % 2 == 0 else GRAY4)
            fw = "bold" if j == 0 else "normal"
            draw_box(
                ax,
                x,
                y,
                w - 0.05,
                row_h - 0.02,
                cell,
                fill=fill,
                fontsize=6,
                fontweight=fw,
                rounded=False,
            )

    # Note
    ax.text(
        5.0,
        0.5,
        "Vendor lock-in: program w RAPID ≠ działa na KUKA. "
        "ROS/ROS 2 jako warstwa unifikująca.",
        ha="center",
        va="center",
        fontsize=7,
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.8,
        },
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "robot_vendor_comparison.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)
    _logger.info("Generated robot_vendor_comparison.png")
