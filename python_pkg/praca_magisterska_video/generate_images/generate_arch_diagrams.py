#!/usr/bin/env python3
"""Generate architecture modeling diagrams for PYTANIE 13 (AIS).

  1. TOGAF ADM cycle
  2. 4+1 View Model (Kruchten)
  3. C4 Model — 4 zoom levels
  4. Zachman Framework grid
  5. ArchiMate layers.

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 9
FS_TITLE = 14
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# Light grays for B&W contrast
GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"


def draw_arrow(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    lw: float = 1.3,
) -> None:
    """Draw arrow."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "color": LN, "lw": lw},
    )


def draw_line(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    lw: float = 1.3,
    ls: str = "-",
) -> None:
    """Draw line."""
    ax.plot([x1, x2], [y1, y2], color=LN, lw=lw, linestyle=ls)


def draw_box(
    ax: Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fill: str = "white",
    lw: float = 1.5,
    fontsize: float = FS,
    fontweight: str = "normal",
    ha: str = "center",
    va: str = "center",
    *,
    rounded: bool = False,
) -> None:
    """Draw box."""
    if rounded:
        rect = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.2", lw=lw, edgecolor=LN, facecolor=fill
        )
    else:
        rect = plt.Rectangle((x, y), w, h, lw=lw, edgecolor=LN, facecolor=fill)
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha=ha,
        va=va,
        fontsize=fontsize,
        fontweight=fontweight,
        wrap=True,
    )


def _draw_class(
    ax: Axes,
    x: float,
    y: float,
    name: str,
    attrs: list[str],
    methods: list[str],
    w: float = 28,
    fill: str = GRAY1,
) -> None:
    """Draw UML-style class box."""
    h_name = 6
    h_attr = len(attrs) * 4 + 2
    h_meth = len(methods) * 4 + 2
    h_total = h_name + h_attr + h_meth
    ax.add_patch(
        plt.Rectangle(
            (x, y),
            w,
            h_total,
            lw=1.5,
            edgecolor=LN,
            facecolor=fill,
        )
    )
    ax.plot(
        [x, x + w],
        [y + h_total - h_name, y + h_total - h_name],
        color=LN,
        lw=1,
    )
    ax.text(
        x + w / 2,
        y + h_total - h_name / 2,
        name,
        ha="center",
        va="center",
        fontsize=7,
        fontweight="bold",
    )
    ax.plot(
        [x, x + w],
        [y + h_meth, y + h_meth],
        color=LN,
        lw=1,
    )
    for i, a in enumerate(attrs):
        ax.text(
            x + 2,
            y + h_total - h_name - 2 - i * 4,
            a,
            fontsize=6,
            va="top",
            family="monospace",
        )
    for i, m in enumerate(methods):
        ax.text(
            x + 2,
            y + h_meth - 2 - i * 4,
            m,
            fontsize=6,
            va="top",
            family="monospace",
        )


from python_pkg.praca_magisterska_video.generate_images._arch_c4 import (
    generate_c4,
)
from python_pkg.praca_magisterska_video.generate_images._arch_layers import (
    generate_archimate,
    generate_zachman,
)


# =========================================================================
# 1. TOGAF ADM Cycle
# =========================================================================
def generate_togaf_adm() -> None:
    """Generate togaf adm."""
    fig, ax = plt.subplots(figsize=(8.27, 8.27))
    ax.set_xlim(-12, 12)
    ax.set_ylim(-12, 12)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "TOGAF ADM (Architecture Development Method)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=15,
    )

    # Center: Requirements Management
    c = plt.Circle((0, 0), 2.5, lw=2, edgecolor=LN, facecolor=GRAY2)
    ax.add_patch(c)
    ax.text(
        0,
        0,
        "Requirements\nManagement",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
    )

    # Phases around the circle
    phases = [
        ("Preliminary", 90),
        ("A: Architecture\nVision", 45),
        ("B: Business\nArchitecture", 0),
        ("C: Information\nSystems Arch.", -45),
        ("D: Technology\nArchitecture", -90),
        ("E: Opportunities\n& Solutions", -135),
        ("F: Migration\nPlanning", 180),
        ("G: Implementation\nGovernance", 135),
    ]

    radius = 8  # radius of phase placement
    box_w = 4.5
    box_h = 2.2

    for i, (label, angle_deg) in enumerate(phases):
        angle = np.radians(angle_deg)
        cx = radius * np.cos(angle)
        cy = radius * np.sin(angle)

        fill = GRAY1 if i % 2 == 0 else GRAY4
        rect = FancyBboxPatch(
            (cx - box_w / 2, cy - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.2",
            lw=1.5,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(cx, cy, label, ha="center", va="center", fontsize=7, fontweight="bold")

        # Arrow from this phase toward center (representing link to Requirements)
        inner_r = 2.8
        ix = inner_r * np.cos(angle)
        iy = inner_r * np.sin(angle)
        outer_r = radius - box_w / 2 - 0.3
        ox = outer_r * np.cos(angle)
        oy = outer_r * np.sin(angle)
        # Dashed line to center
        draw_line(ax, ix, iy, ox * 0.75, oy * 0.75, lw=0.6, ls="--")

    # Curved arrows between successive phases (outer ring)
    for i in range(len(phases)):
        a1 = np.radians(phases[i][1])
        a2 = np.radians(phases[(i + 1) % len(phases)][1])

        # Midpoint arc arrow
        mid_angle = (a1 + a2) / 2
        if phases[i][1] < phases[(i + 1) % len(phases)][1]:
            mid_angle += np.pi  # handle wrap
        ar = radius + 0.3
        ar * np.cos(mid_angle)
        ar * np.sin(mid_angle)

        # Simple arrow from phase i endpoint to phase i+1 start
        # arrow a bit outside the boxes
        src_angle = a1 - np.radians(18)
        dst_angle = a2 + np.radians(18)
        sx = (radius + 2.8) * np.cos(src_angle)
        sy = (radius + 2.8) * np.sin(src_angle)
        dx = (radius + 2.8) * np.cos(dst_angle)
        dy = (radius + 2.8) * np.sin(dst_angle)

        ax.annotate(
            "",
            xy=(dx, dy),
            xytext=(sx, sy),
            arrowprops={
                "arrowstyle": "->",
                "color": LN,
                "lw": 1,
                "connectionstyle": "arc3,rad=0.3",
            },
        )

    # Legend note
    ax.text(
        0,
        -11.5,
        "Cykl iteracyjny: każda faza"
        " może wracać do wcześniejszych.\n"
        "Requirements Management w centrum"
        " — wpływa na każdą fazę.",
        ha="center",
        va="center",
        fontsize=7,
        fontstyle="italic",
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "togaf_adm.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK TOGAF ADM")


# =========================================================================
# 2. 4+1 View Model  (Kruchten)
# =========================================================================
def generate_4plus1() -> None:
    """Generate 4plus1."""
    fig, ax = plt.subplots(figsize=(8.27, 6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 65)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "4+1 View Model (Kruchten, 1995)", fontsize=FS_TITLE, fontweight="bold", pad=12
    )

    cx, cy = 50, 32
    cw, ch = 18, 8
    draw_box(
        ax,
        cx - cw / 2,
        cy - ch / 2,
        cw,
        ch,
        "+1\nScenarios\n(Use Cases)",
        fill=GRAY2,
        lw=2,
        fontsize=9,
        fontweight="bold",
        rounded=True,
    )

    # 4 views around
    views = [
        (
            "Logical View\n(Funkcjonalno\u015b\u0107:\nklasy, modu\u0142y)",
            cx,
            cy + 18,
            "Programista",
        ),
        (
            "Process View\n(Współbieżność,\nprzepływ danych)",
            cx + 28,
            cy,
            "Integrator",
        ),
        (
            "Development View\n(Organizacja kodu:\npakiety, warstwy)",
            cx,
            cy - 18,
            "Developer",
        ),
        (
            "Physical View\n(Wdro\u017cenie:\nserwery, kontenery)",
            cx - 28,
            cy,
            "Admin/DevOps",
        ),
    ]

    bw, bh = 22, 10
    for label, vx, vy, stakeholder in views:
        draw_box(
            ax,
            vx - bw / 2,
            vy - bh / 2,
            bw,
            bh,
            label,
            fill=GRAY1,
            lw=1.5,
            fontsize=8,
            fontweight="bold",
            rounded=True,
        )
        # Label stakeholder below/beside
        if vy > cy:
            ax.text(
                vx,
                vy + bh / 2 + 1.5,
                f"\u2190 {stakeholder}",
                fontsize=7,
                ha="center",
                fontstyle="italic",
            )
        elif vy < cy:
            ax.text(
                vx,
                vy - bh / 2 - 1.5,
                f"\u2190 {stakeholder}",
                fontsize=7,
                ha="center",
                fontstyle="italic",
            )
        elif vx > cx:
            ax.text(
                vx + bw / 2 + 1,
                vy,
                f"\u2190 {stakeholder}",
                fontsize=7,
                va="center",
                fontstyle="italic",
            )
        else:
            ax.text(
                vx - bw / 2 - 1,
                vy,
                f"{stakeholder} \u2192",
                fontsize=7,
                va="center",
                ha="right",
                fontstyle="italic",
            )

        # Arrow from view to center
        # Calculate direction
        dx = cx - vx
        dy = cy - vy
        dist = np.sqrt(dx**2 + dy**2)
        ndx, ndy = dx / dist, dy / dist
        # Start from edge of view box, end at edge of center box
        sx = vx + ndx * (bw / 2 + 0.5) if abs(dx) > abs(dy) else vx + ndx * 2
        sy = vy + ndy * (bh / 2 + 0.5) if abs(dy) > abs(dx) else vy + ndy * 2
        ex = cx - ndx * (cw / 2 + 0.5) if abs(dx) > abs(dy) else cx - ndx * 2
        ey = cy - ndy * (ch / 2 + 0.5) if abs(dy) > abs(dx) else cy - ndy * 2

        draw_arrow(ax, sx, sy, ex, ey, lw=1.2)

    # Note
    ax.text(
        50,
        2,
        "Ka\u017cdy widok odpowiada innemu interesariuszowi.\n"
        "Scenarios (łączący +1) weryfikują"
        " spójność 4 widoków.",
        ha="center",
        fontsize=7,
        fontstyle="italic",
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "4plus1_view_model.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK 4+1 View Model")


# =========================================================================
if __name__ == "__main__":
    _logger.info(
        "Generating architecture diagrams to %s/...",
        OUTPUT_DIR,
    )
    generate_togaf_adm()
    generate_4plus1()
    generate_c4()
    generate_zachman()
    generate_archimate()
    _logger.info("All diagrams saved to %s/", OUTPUT_DIR)
    for diagram_file in sorted(p.name for p in Path(OUTPUT_DIR).iterdir()):
        if (
            "togaf" in diagram_file
            or "4plus1" in diagram_file
            or "c4" in diagram_file
            or "zachman" in diagram_file
            or "archimate" in diagram_file
        ):
            size_kb = Path(str(Path(OUTPUT_DIR).stat().st_size / diagram_file)) / 1024
            _logger.info(
                "  %s (%.0f KB)",
                diagram_file,
                size_kb,
            )
