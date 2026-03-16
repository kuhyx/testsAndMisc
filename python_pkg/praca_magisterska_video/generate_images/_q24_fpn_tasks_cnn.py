"""FPN, anchor boxes, detection tasks, and CNN architecture diagrams."""

from __future__ import annotations

from _q24_common import (
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    draw_arrow,
    draw_box,
    np,
    plt,
    save_fig,
)
import matplotlib.patches as mpatches


# ============================================================
# 16. FPN (Feature Pyramid Network)
# ============================================================
def draw_fpn() -> None:
    """Draw fpn."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "FPN (Feature Pyramid Network) — detekcja obiektów wszystkich rozmiarów",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    levels = [
        (0, 0, 2.0, 2.0, "C2\n56x56", "duże\ndetale"),
        (0, 2.2, 1.5, 1.5, "C3\n28x28", ""),
        (0, 3.9, 1.0, 1.0, "C4\n14x14", ""),
        (0, 5.1, 0.6, 0.6, "C5\n7x7", "kontekst"),
    ]

    for x, y, w, h, label, note in levels:
        ax.add_patch(
            mpatches.Rectangle((x, y - h), w, h, facecolor=GRAY4, edgecolor=LN, lw=1.5)
        )
        ax.text(
            x + w / 2,
            y - h / 2,
            label,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontweight="bold",
        )
        if note:
            ax.text(
                x + w + 0.15,
                y - h / 2,
                note,
                ha="left",
                va="center",
                fontsize=5,
                style="italic",
            )

    ax.text(
        1.0, -0.3, "Bottom-up\n(backbone)", ha="center", fontsize=FS, fontweight="bold"
    )

    # Top-down + lateral
    td_levels = [
        (4.5, 5.1, 0.6, 0.6, "P5"),
        (4.5, 3.9, 1.0, 1.0, "P4"),
        (4.5, 2.2, 1.5, 1.5, "P3"),
        (4.5, 0, 2.0, 2.0, "P2"),
    ]

    for x, y, w, h, label in td_levels:
        ax.add_patch(
            mpatches.Rectangle(
                (x, y - h + h), w, h, facecolor=GRAY2, edgecolor=LN, lw=1.5
            )
        )
        ax.text(
            x + w / 2,
            y - h / 2 + h,
            label,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontweight="bold",
        )

    # Lateral connections
    for (_, y1, w1, h1, _, _), (x2, y2, _w2, h2, _) in zip(
        levels, td_levels, strict=False
    ):
        draw_arrow(ax, w1 + 0.2, y1 - h1 / 2, x2 - 0.1, y2 + h2 / 2, lw=1, style="->")

    # Top-down arrows
    for i in range(len(td_levels) - 1):
        x2, y2, w2, h2, _ = td_levels[i]
        x3, y3, w3, h3, _ = td_levels[i + 1]
        draw_arrow(
            ax,
            x2 + w2 / 2,
            y2,
            x3 + w3 / 2,
            y3 + h3 + 0.1,
            lw=1.2,
            style="->",
            color=GRAY3,
        )

    ax.text(
        5.5,
        -0.3,
        "Top-down + lateral\n(FPN)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
    )

    # Detection outputs
    det_labels = ["małe obj.", "średnie", "duże", "b. duże"]
    for i, (x, y, w, h, _label) in enumerate(td_levels):
        draw_arrow(ax, x + w + 0.1, y + h / 2, 7.5, y + h / 2, lw=0.8)
        ax.text(
            7.7,
            y + h / 2,
            f"detekcja:\n{det_labels[3 - i]}",
            fontsize=FS_SMALL,
            va="center",
        )

    save_fig(fig, "q24_fpn.png")


# ============================================================
# 17. Anchor boxes
# ============================================================
def draw_anchor_boxes() -> None:
    """Draw anchor boxes."""
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title(
        "Anchor boxes — predefiniowane kształty",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    ax.add_patch(mpatches.Rectangle((0, 0), 6, 5, facecolor=GRAY4, edgecolor=LN, lw=1))

    # Center point
    cx, cy = 3, 2.5
    ax.plot(cx, cy, "ko", markersize=8, zorder=5)
    ax.text(cx + 0.15, cy + 0.15, "(x, y)", fontsize=FS, fontweight="bold")

    # 9 anchors: 3 sizes x 3 ratios
    anchors = [
        (0.8, 0.8, "-", "1:1 small"),
        (1.6, 1.6, "-", "1:1 medium"),
        (2.4, 2.4, "-", "1:1 large"),
        (0.6, 1.2, "--", "1:2 small"),
        (1.2, 2.4, "--", "1:2 medium"),
        (1.8, 3.6, "--", "1:2 large"),
        (1.2, 0.6, ":", "2:1 small"),
        (2.4, 1.2, ":", "2:1 medium"),
        (3.6, 1.8, ":", "2:1 large"),
    ]

    for w, h, ls, _label in anchors:
        rect = mpatches.Rectangle(
            (cx - w / 2, cy - h / 2),
            w,
            h,
            facecolor="none",
            edgecolor=LN,
            lw=1.2,
            linestyle=ls,
        )
        ax.add_patch(rect)

    # Legend-style labels
    ax.text(
        3,
        -0.5,
        "9 anchorów = 3 rozmiary x 3 proporcje (1:1, 1:2, 2:1)\n"
        "Sieć predykuje PRZESUNIĘCIE od najbliższego anchora",
        ha="center",
        fontsize=FS,
        style="italic",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-1.2, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")

    save_fig(fig, "q24_anchor_boxes.png")


# ============================================================
# 18. Detection task comparison
# ============================================================
def draw_detection_tasks() -> None:
    """Draw detection tasks."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle(
        "Klasyfikacja vs Detekcja vs Segmentacja",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Classification
    ax = axes[0]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 4, 4, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    # Simple cat silhouette
    ax.add_patch(mpatches.Ellipse((2, 2), 2, 1.5, facecolor=GRAY3, edgecolor=LN, lw=1))
    ax.add_patch(mpatches.Ellipse((2, 3), 1, 0.8, facecolor=GRAY3, edgecolor=LN, lw=1))
    # Ears
    ax.plot([1.6, 1.5, 1.8], [3.3, 3.8, 3.4], color=LN, lw=1.5)
    ax.plot([2.2, 2.5, 2.4], [3.3, 3.8, 3.4], color=LN, lw=1.5)
    ax.text(
        2, -0.4, '→ "KOT" (jedna etykieta)', ha="center", fontsize=FS, fontweight="bold"
    )
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.8, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Klasyfikacja\n(co?)", fontsize=FS, fontweight="bold")

    # Detection
    ax = axes[1]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 4, 4, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    # Cat
    ax.add_patch(
        mpatches.Ellipse((1.2, 2), 1.2, 1, facecolor=GRAY3, edgecolor=LN, lw=1)
    )
    ax.add_patch(
        mpatches.Ellipse((1.2, 2.8), 0.7, 0.5, facecolor=GRAY3, edgecolor=LN, lw=1)
    )
    # Dog
    ax.add_patch(
        mpatches.Ellipse((3, 1.5), 1.2, 1, facecolor=GRAY2, edgecolor=LN, lw=1)
    )
    ax.add_patch(
        mpatches.Ellipse((3, 2.3), 0.7, 0.5, facecolor=GRAY2, edgecolor=LN, lw=1)
    )
    # Bounding boxes
    ax.add_patch(
        mpatches.Rectangle((0.3, 1.2), 1.8, 2.2, facecolor="none", edgecolor=LN, lw=2.5)
    )
    ax.text(1.2, 3.5, "KOT", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.add_patch(
        mpatches.Rectangle((2.1, 0.8), 1.7, 2.0, facecolor="none", edgecolor=LN, lw=2.5)
    )
    ax.text(3.0, 2.9, "PIES", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.text(
        2,
        -0.4,
        "→ bbox + klasa (N obiektów)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
    )
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.8, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Detekcja\n(co? + gdzie?)", fontsize=FS, fontweight="bold")

    # Segmentation
    ax = axes[2]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 4, 4, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    # Cat mask (detailed)
    theta = np.linspace(0, 2 * np.pi, 30)
    cat_x = 1.2 + 0.6 * np.cos(theta) + 0.1 * np.sin(3 * theta)
    cat_y = 2 + 0.5 * np.sin(theta) + 0.1 * np.cos(2 * theta)
    ax.fill(cat_x, cat_y, facecolor=GRAY3, edgecolor=LN, lw=1.5)
    # Dog mask
    dog_x = 3.0 + 0.6 * np.cos(theta) + 0.05 * np.sin(4 * theta)
    dog_y = 1.5 + 0.5 * np.sin(theta) + 0.08 * np.cos(3 * theta)
    ax.fill(dog_x, dog_y, facecolor=GRAY2, edgecolor=LN, lw=1.5)
    ax.text(1.2, 2, "KOT", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.text(3.0, 1.5, "PIES", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.text(
        2,
        -0.4,
        "→ maska pikseli (per piksel)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
    )
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.8, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Segmentacja\n(dokładna maska)", fontsize=FS, fontweight="bold")

    fig.tight_layout()
    save_fig(fig, "q24_detection_tasks.png")


# ============================================================
# 19. CNN Architecture overview
# ============================================================
def draw_cnn_architecture() -> None:
    """Draw cnn architecture."""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(-0.5, 12.5)
    ax.set_ylim(-1, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "CNN — od obrazu do predykcji (architektura)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    # Input image
    draw_box(ax, 0, 0.5, 1.5, 3, "Obraz\n224x224x3", fill=GRAY1, fontsize=FS)

    # Conv1
    draw_arrow(ax, 1.6, 2.0, 2.1, 2.0, lw=1.2)
    draw_box(
        ax, 2.2, 0.8, 1.2, 2.4, "Conv1\n+ReLU\n55x55x96", fill=GRAY4, fontsize=FS_SMALL
    )

    # Pool1
    draw_arrow(ax, 3.5, 2.0, 3.9, 2.0, lw=1.2)
    draw_box(ax, 4.0, 1.0, 1.0, 2.0, "Pool\n27x27\nx96", fill=GRAY2, fontsize=FS_SMALL)

    # Conv2
    draw_arrow(ax, 5.1, 2.0, 5.5, 2.0, lw=1.2)
    draw_box(
        ax,
        5.6,
        0.8,
        1.2,
        2.4,
        "Conv2\n+ReLU\n27x27\nx256",
        fill=GRAY4,
        fontsize=FS_SMALL,
    )

    # Pool2
    draw_arrow(ax, 6.9, 2.0, 7.3, 2.0, lw=1.2)
    draw_box(ax, 7.4, 1.2, 0.8, 1.6, "Pool\n13x13\nx256", fill=GRAY2, fontsize=FS_SMALL)

    # More conv...
    draw_arrow(ax, 8.3, 2.0, 8.7, 2.0, lw=1.2)
    ax.text(9.0, 2.0, "...", fontsize=14, ha="center", va="center")
    draw_arrow(ax, 9.3, 2.0, 9.7, 2.0, lw=1.2)

    # FC
    draw_box(ax, 9.8, 1.2, 1.0, 1.6, "FC\n4096", fill=GRAY3, fontsize=FS)

    draw_arrow(ax, 10.9, 2.0, 11.3, 2.0, lw=1.2)

    # Output
    draw_box(
        ax, 11.4, 1.5, 1.0, 1.0, "Softmax\n1000 klas", fill=GRAY1, fontsize=FS_SMALL
    )

    # Annotations below
    ax.text(
        3.0,
        0.0,
        "rozmiar maleje\n224→55→27→13→6",
        ha="center",
        fontsize=FS_SMALL,
        style="italic",
    )
    ax.text(
        6.0,
        0.0,
        "kanały rosną\n3→96→256→384",
        ha="center",
        fontsize=FS_SMALL,
        style="italic",
    )
    ax.text(
        10.0, 0.0, "decyzja\nkońcowa", ha="center", fontsize=FS_SMALL, style="italic"
    )

    # hierarchy
    ax.text(
        6.0,
        4.0,
        "Hierarchia: krawędzie → rogi → fragmenty → obiekty (K-R-F-O)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    save_fig(fig, "q24_cnn_architecture.png")
