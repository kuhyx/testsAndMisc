"""R-CNN evolution and YOLO grid diagrams."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q24_common import (
    FS,
    FS_LABEL,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    draw_arrow,
    draw_box,
    plt,
    save_fig,
)
import matplotlib.patches as mpatches

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _draw_yolo_cell_prediction(ax: Axes) -> None:
    """Draw YOLO cell prediction vector panel."""
    ax.axis("off")
    ax.set_xlim(0, 6)
    ax.set_ylim(-1, 5)

    labels = [
        "x",
        "y",
        "w",
        "h",
        "conf",
        "x",
        "y",
        "w",
        "h",
        "conf",
        "P(c₁)",
        "...",
        "P(c₂₀)",
    ]
    colors_vec = [GRAY4] * 5 + [GRAY2] * 5 + [GRAY1] * 3

    bw = 0.42
    for i, (label, col) in enumerate(
        zip(labels, colors_vec, strict=False),
    ):
        x_pos = 0.3 + i * bw
        ax.add_patch(
            mpatches.Rectangle(
                (x_pos, 2.5),
                bw - 0.02,
                0.6,
                facecolor=col,
                edgecolor=LN,
                lw=0.8,
            )
        )
        ax.text(
            x_pos + bw / 2,
            2.8,
            label,
            ha="center",
            va="center",
            fontsize=5,
            fontweight="bold",
        )

    ax.annotate(
        "",
        xy=(0.3, 2.4),
        xytext=(2.4, 2.4),
        arrowprops={"arrowstyle": "-", "lw": 1},
    )
    ax.text(1.35, 2.15, "bbox 1 (5 wartości)", ha="center", fontsize=FS_SMALL)

    ax.annotate(
        "",
        xy=(2.4, 2.4),
        xytext=(4.5, 2.4),
        arrowprops={"arrowstyle": "-", "lw": 1},
    )
    ax.text(3.45, 2.15, "bbox 2 (5 wartości)", ha="center", fontsize=FS_SMALL)

    ax.annotate(
        "",
        xy=(4.5, 2.4),
        xytext=(5.8, 2.4),
        arrowprops={"arrowstyle": "-", "lw": 1},
    )
    ax.text(5.15, 2.15, "20 klas", ha="center", fontsize=FS_SMALL)

    ax.text(
        3.0,
        3.5,
        "Każda komórka → 30 wartości\n= 2x(x,y,w,h,conf) + 20 klas",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.set_title(
        "② Predykcja jednej komórki\n(S=7, B=2, C=20)",
        fontsize=FS,
        fontweight="bold",
    )


# ============================================================
# 6. R-CNN Evolution
# ============================================================
def draw_rcnn_evolution() -> None:
    """Draw rcnn evolution."""
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(-0.5, 11)
    ax.set_ylim(-0.5, 7.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Ewolucja R-CNN: od 50s do 0.2s na obraz",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    y_positions = [5.5, 3.0, 0.5]
    labels = [
        "R-CNN (2014) — 50 s/obraz",
        "Fast R-CNN (2015) — 2 s/obraz",
        "Faster R-CNN (2015) — 0.2 s/obraz",
    ]

    # R-CNN
    y = y_positions[0]
    ax.text(0, y + 1.3, labels[0], fontsize=FS_LABEL, fontweight="bold")
    draw_box(ax, 0, y, 2, 0.9, "Selective\nSearch", fill=GRAY2, fontsize=FS)
    draw_arrow(ax, 2.1, y + 0.45, 2.5, y + 0.45)
    ax.text(2.3, y + 0.8, "~2000", ha="center", fontsize=FS_SMALL, style="italic")
    draw_box(ax, 2.6, y, 1.5, 0.9, "Resize\n224x224", fill=GRAY4, fontsize=FS)
    draw_arrow(ax, 4.2, y + 0.45, 4.6, y + 0.45)
    draw_box(
        ax, 4.7, y, 1.5, 0.9, "CNN\nx2000!", fill=GRAY3, fontsize=FS, fontweight="bold"
    )
    draw_arrow(ax, 6.3, y + 0.45, 6.7, y + 0.45)
    draw_box(ax, 6.8, y, 1.3, 0.9, "SVM\nklasyf.", fill=GRAY4, fontsize=FS)
    draw_arrow(ax, 8.2, y + 0.45, 8.6, y + 0.45)
    draw_box(ax, 8.7, y, 1.0, 0.9, "NMS", fill=GRAY1, fontsize=FS)
    # Problem annotation
    ax.text(
        5.5,
        y - 0.4,
        "⚠ CNN uruchamiane 2000x → 50 sek!",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # Fast R-CNN
    y = y_positions[1]
    ax.text(0, y + 1.3, labels[1], fontsize=FS_LABEL, fontweight="bold")
    draw_box(ax, 0, y, 2, 0.9, "Selective\nSearch", fill=GRAY2, fontsize=FS)
    draw_arrow(ax, 2.1, y + 0.45, 2.5, y + 0.45)
    draw_box(
        ax,
        2.6,
        y,
        1.5,
        0.9,
        "CNN\nx1 (RAZ!)",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 4.2, y + 0.45, 4.6, y + 0.45)
    draw_box(
        ax, 4.7, y, 1.5, 0.9, "ROI\nPooling", fill=GRAY1, fontsize=FS, fontweight="bold"
    )
    draw_arrow(ax, 6.3, y + 0.45, 6.7, y + 0.45)
    draw_box(ax, 6.8, y, 1.3, 0.9, "FC\nklasa+bbox", fill=GRAY4, fontsize=FS)
    draw_arrow(ax, 8.2, y + 0.45, 8.6, y + 0.45)
    draw_box(ax, 8.7, y, 1.0, 0.9, "NMS", fill=GRAY1, fontsize=FS)
    ax.text(
        3.8,
        y - 0.4,
        "✓ CNN RAZ na cały obraz → 25x szybciej",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # Faster R-CNN
    y = y_positions[2]
    ax.text(0, y + 1.3, labels[2], fontsize=FS_LABEL, fontweight="bold")
    draw_box(
        ax,
        0.5,
        y,
        1.5,
        0.9,
        "CNN\nBackbone",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 2.1, y + 0.45, 2.5, y + 0.45)
    draw_box(ax, 2.6, y, 1.5, 0.9, "Feature\nMap", fill=GRAY1, fontsize=FS)
    draw_arrow(ax, 4.2, y + 0.45, 4.6, y + 0.45)
    draw_box(
        ax,
        4.7,
        y,
        1.3,
        0.9,
        "RPN\n(w sieci!)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 6.1, y + 0.45, 6.5, y + 0.45)
    draw_box(ax, 6.6, y, 1.3, 0.9, "ROI\nPooling", fill=GRAY1, fontsize=FS)
    draw_arrow(ax, 8.0, y + 0.45, 8.4, y + 0.45)
    draw_box(ax, 8.5, y, 1.3, 0.9, "FC\nklasa+bbox", fill=GRAY4, fontsize=FS)
    ax.text(
        5.0,
        y - 0.4,
        "✓ RPN zastępuje Selective Search → end-to-end",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    save_fig(fig, "q24_rcnn_evolution.png")


# ============================================================
# 7. YOLO Grid
# ============================================================
def draw_yolo_grid() -> None:
    """Draw yolo grid."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle(
        "YOLO — detekcja jednoetapowa (siatka SxS)",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Grid on image
    ax = axes[0]
    grid_size = 7
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)
    for i in range(grid_size + 1):
        ax.axhline(y=i, color=LN, lw=0.5, alpha=0.5)
        ax.axvline(x=i, color=LN, lw=0.5, alpha=0.5)
    ax.add_patch(
        mpatches.Rectangle(
            (0, 0),
            grid_size,
            grid_size,
            facecolor=GRAY4,
            edgecolor=LN,
            lw=1.5,
        )
    )
    # Highlight one cell
    ax.add_patch(mpatches.Rectangle((3, 3), 1, 1, facecolor=GRAY2, edgecolor=LN, lw=2))
    # Object center dot
    ax.plot(3.5, 3.5, "ko", markersize=8)
    # Bounding box from that cell
    ax.add_patch(
        mpatches.Rectangle(
            (2.0, 2.2), 3.0, 2.6, facecolor="none", edgecolor=LN, lw=2, linestyle="--"
        )
    )
    ax.text(
        3.5,
        1.8,
        "bbox z komórki (3,3)",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title("① Siatka 7x7\nna obrazie", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    _draw_yolo_cell_prediction(axes[1])

    # Speed comparison
    ax = axes[2]
    ax.axis("off")
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 5)

    methods = ["R-CNN", "Fast R-CNN", "Faster R-CNN", "YOLO", "YOLOv8"]
    fps_vals = [0.02, 0.5, 5, 45, 100]
    bar_colors = [GRAY3, GRAY3, GRAY3, GRAY2, GRAY1]

    for i, (m, f, c) in enumerate(zip(methods, fps_vals, bar_colors, strict=False)):
        bar_w = f / 100 * 4.0
        y_pos = 4.0 - i * 0.8
        ax.add_patch(
            mpatches.Rectangle(
                (0.5, y_pos), max(bar_w, 0.1), 0.5, facecolor=c, edgecolor=LN, lw=0.8
            )
        )
        ax.text(
            0.4,
            y_pos + 0.25,
            m,
            ha="right",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )
        ax.text(
            max(0.7, 0.5 + bar_w + 0.1),
            y_pos + 0.25,
            f"{f} fps",
            ha="left",
            va="center",
            fontsize=FS,
        )

    ax.set_title(
        "③ Porównanie szybkości\n(fps = klatki/sek)", fontsize=FS, fontweight="bold"
    )

    fig.tight_layout()
    save_fig(fig, "q24_yolo_grid.png")
