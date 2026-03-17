"""Robot movement types, online/offline, ROS, RAPID."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from python_pkg.praca_magisterska_video.generate_images.generate_robot_lang_diagrams import (
    BG,
    DPI,
    FS_TITLE,
    GRAY2,
    GRAY4,
    GRAY5,
    OUTPUT_DIR,
    WHITE,
    draw_arrow,
    draw_box,
)

_logger = logging.getLogger(__name__)



# ============================================================
# 3. Robot Movement Types (PTP, LIN, CIRC)
# ============================================================
def _draw_ptp_subplot(ax: Axes) -> None:
    """Draw the PTP (Point-to-Point) subplot."""
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.5, 4.5)
    ax.set_aspect("equal")
    ax.set_title(
        "PTP (Point-to-Point)\nMoveJ / PTP",
        fontsize=8,
        fontweight="bold",
    )
    ax.grid(visible=True, alpha=0.3)

    start = (0.5, 0.5)
    end = (3.5, 3.5)
    ax.plot(*start, "ko", ms=10, zorder=5)
    ax.plot(*end, "ks", ms=10, zorder=5)
    ax.text(start[0] - 0.3, start[1] - 0.3, "Start", fontsize=7, ha="center")
    ax.text(end[0] + 0.3, end[1] + 0.3, "Cel", fontsize=7, ha="center")

    # Curved path (joint space = not necessarily straight in Cartesian)
    t = np.linspace(0, 1, 50)
    x_ptp = start[0] + (end[0] - start[0]) * t + 0.8 * np.sin(np.pi * t)
    y_ptp = start[1] + (end[1] - start[1]) * t - 0.3 * np.sin(np.pi * t)
    ax.plot(x_ptp, y_ptp, "k-", lw=2)
    ax.annotate(
        "",
        xy=(x_ptp[-1], y_ptp[-1]),
        xytext=(x_ptp[-3], y_ptp[-3]),
        arrowprops={"arrowstyle": "->", "color": "black", "lw": 2},
    )

    ax.text(
        2.8,
        1.2,
        "Ścieżka\nw kartezjańskiej\nnieokreślona!",
        fontsize=6,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round", "facecolor": GRAY4, "edgecolor": GRAY5},
    )
    ax.text(
        2.0,
        -0.3,
        "Najszybszy, ale\nścieżka nieprzewidywalna",
        fontsize=6,
        ha="center",
        style="italic",
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(labelsize=6)


def _draw_lin_subplot(ax: Axes) -> None:
    """Draw the LIN (Linear) subplot."""
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.5, 4.5)
    ax.set_aspect("equal")
    ax.set_title(
        "LIN (Linear)\nMoveL / LIN",
        fontsize=8,
        fontweight="bold",
    )
    ax.grid(visible=True, alpha=0.3)

    start = (0.5, 1.0)
    end = (3.5, 3.5)
    ax.plot(*start, "ko", ms=10, zorder=5)
    ax.plot(*end, "ks", ms=10, zorder=5)
    ax.text(start[0] - 0.3, start[1] - 0.3, "Start", fontsize=7, ha="center")
    ax.text(end[0] + 0.3, end[1] + 0.3, "Cel", fontsize=7, ha="center")

    # Straight line
    ax.plot([start[0], end[0]], [start[1], end[1]], "k-", lw=2)
    ax.annotate(
        "",
        xy=end,
        xytext=(
            start[0] + 0.9 * (end[0] - start[0]),
            start[1] + 0.9 * (end[1] - start[1]),
        ),
        arrowprops={"arrowstyle": "->", "color": "black", "lw": 2},
    )

    # Show intermediate points
    for frac in [0.25, 0.5, 0.75]:
        px = start[0] + frac * (end[0] - start[0])
        py = start[1] + frac * (end[1] - start[1])
        ax.plot(px, py, "k.", ms=6)

    ax.text(
        2.0,
        -0.3,
        "Prosta linia TCP\nIK w każdym punkcie",
        fontsize=6,
        ha="center",
        style="italic",
    )
    ax.tick_params(labelsize=6)


def _draw_circ_subplot(ax: Axes) -> None:
    """Draw the CIRC (Circular) subplot."""
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.5, 4.5)
    ax.set_aspect("equal")
    ax.set_title(
        "CIRC (Circular)\nMoveC / CIRC",
        fontsize=8,
        fontweight="bold",
    )
    ax.grid(visible=True, alpha=0.3)

    # Arc through 3 points
    center = (2.0, 1.5)
    radius = 2.0
    theta_start = np.radians(20)
    theta_end = np.radians(160)
    theta = np.linspace(theta_start, theta_end, 50)
    x_circ = center[0] + radius * np.cos(theta)
    y_circ = center[1] + radius * np.sin(theta)

    ax.plot(x_circ, y_circ, "k-", lw=2)
    ax.annotate(
        "",
        xy=(x_circ[-1], y_circ[-1]),
        xytext=(x_circ[-3], y_circ[-3]),
        arrowprops={"arrowstyle": "->", "color": "black", "lw": 2},
    )

    # Start, auxiliary, end points
    ax.plot(x_circ[0], y_circ[0], "ko", ms=10, zorder=5)
    ax.plot(x_circ[24], y_circ[24], "k^", ms=8, zorder=5)
    ax.plot(x_circ[-1], y_circ[-1], "ks", ms=10, zorder=5)
    ax.text(x_circ[0] + 0.3, y_circ[0] - 0.3, "Start", fontsize=7)
    ax.text(
        x_circ[24] + 0.05,
        y_circ[24] + 0.25,
        "Pkt\npomocniczy",
        fontsize=6,
        ha="center",
    )
    ax.text(x_circ[-1] - 0.5, y_circ[-1] - 0.3, "Cel", fontsize=7)

    # Center
    ax.plot(*center, "k+", ms=8, mew=1.5)
    ax.text(center[0], center[1] - 0.3, "środek", fontsize=6, ha="center")

    ax.text(
        2.0,
        -0.3,
        "Łuk wyznaczony\nprzez 3 punkty",
        fontsize=6,
        ha="center",
        style="italic",
    )
    ax.tick_params(labelsize=6)


def draw_movement_types() -> None:
    """Draw movement types."""
    fig, axes = plt.subplots(1, 3, figsize=(8.27, 3.2))
    fig.suptitle(
        "Typy ruchu robota: PTP, LIN, CIRC",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=0.98,
    )

    _draw_ptp_subplot(axes[0])
    _draw_lin_subplot(axes[1])
    _draw_circ_subplot(axes[2])

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "robot_movement_types.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)
    _logger.info("Generated robot_movement_types.png")


# ============================================================
# 4. Online vs Offline Programming
# ============================================================
def draw_online_offline() -> None:
    """Draw online offline."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Programowanie robotów: Online (teach-in) vs Offline",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # === ONLINE side (left) ===
    # Title
    draw_box(
        ax,
        0.3,
        5.2,
        4.2,
        0.8,
        "ONLINE\n(teach-in / pendant)",
        fill=GRAY2,
        fontsize=9,
        fontweight="bold",
    )

    steps_online = [
        (4.2, "Operator przy robocie\nz teach pendantem"),
        (3.2, 'Prowadzi ramię\n„za rękę" do punktów'),
        (2.2, "Robot zapamiętuje\npozycje (record)"),
        (1.2, "Odtwarzanie\nzapisanej ścieżki"),
    ]
    for y, txt in steps_online:
        draw_box(ax, 0.5, y, 3.8, 0.8, txt, fill=WHITE, fontsize=7)

    for i in range(len(steps_online) - 1):
        draw_arrow(ax, 2.4, steps_online[i][0], 2.4, steps_online[i + 1][0] + 0.8)

    # Pros/cons
    ax.text(
        2.4,
        0.6,
        "✓ Proste, intuicyjne\n✗ Wymaga zatrzymania produkcji\n✗ Niska precyzja",
        ha="center",
        va="center",
        fontsize=6.5,
        bbox={"boxstyle": "round", "facecolor": GRAY4, "edgecolor": GRAY5, "lw": 0.8},
    )

    # Divider
    ax.plot([4.9, 4.9], [0.3, 6.2], "k--", lw=1, alpha=0.5)

    # === OFFLINE side (right) ===
    draw_box(
        ax,
        5.3,
        5.2,
        4.2,
        0.8,
        "OFFLINE\n(symulacja / CAD/CAM)",
        fill=GRAY2,
        fontsize=9,
        fontweight="bold",
    )

    steps_offline = [
        (4.2, "Model 3D robota +\nśrodowisko w symulatorze"),
        (3.2, "Programowanie ścieżek\nw środowisku wirtualnym"),
        (2.2, "Weryfikacja kolizji\ni optymalizacja"),
        (1.2, "Transfer na\nrzeczywistego robota"),
    ]
    for y, txt in steps_offline:
        draw_box(ax, 5.5, y, 3.8, 0.8, txt, fill=WHITE, fontsize=7)

    for i in range(len(steps_offline) - 1):
        draw_arrow(ax, 7.4, steps_offline[i][0], 7.4, steps_offline[i + 1][0] + 0.8)

    ax.text(
        7.4,
        0.6,
        "✓ Bez zatrzymania produkcji\n"
        "✓ Wysoka precyzja, symulacja\n"
        "✗ Wymaga kalibracji",
        ha="center",
        va="center",
        fontsize=6.5,
        bbox={"boxstyle": "round", "facecolor": GRAY4, "edgecolor": GRAY5, "lw": 0.8},
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "robot_online_offline.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)
    _logger.info("Generated robot_online_offline.png")


# ============================================================
# 5. ROS Architecture (pub/sub)
# ============================================================
