"""IoU diagram, NMS steps, and detector-from-classifier diagrams."""

from __future__ import annotations

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


# ============================================================
# 8. IoU Diagram
# ============================================================
def draw_iou_diagram() -> None:
    """Draw iou diagram."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
    fig.suptitle(
        "IoU (Intersection over Union) — miara nakładania bboxów",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Low IoU
    ax = axes[0]
    ax.add_patch(
        mpatches.Rectangle(
            (0, 0), 3, 3, facecolor=GRAY4, edgecolor=LN, lw=1.5, label="A"
        )
    )
    ax.add_patch(
        mpatches.Rectangle(
            (2.5, 2.5),
            3,
            3,
            facecolor=GRAY2,
            edgecolor=LN,
            lw=1.5,
            alpha=0.7,
            label="B",
        )
    )
    # Intersection
    ax.add_patch(
        mpatches.Rectangle((2.5, 2.5), 0.5, 0.5, facecolor=GRAY3, edgecolor=LN, lw=2)
    )
    ax.text(1.5, 1.5, "A", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(4, 4, "B", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.set_xlim(-0.5, 6)
    ax.set_ylim(-0.5, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "IoU ≈ 0.04\n(prawie się nie nakładają)", fontsize=FS, fontweight="bold"
    )

    # Medium IoU
    ax = axes[1]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 3, 3, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    ax.add_patch(
        mpatches.Rectangle(
            (1.5, 1.5), 3, 3, facecolor=GRAY2, edgecolor=LN, lw=1.5, alpha=0.7
        )
    )
    ax.add_patch(
        mpatches.Rectangle((1.5, 1.5), 1.5, 1.5, facecolor=GRAY3, edgecolor=LN, lw=2)
    )
    ax.text(0.7, 0.7, "A", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(3.5, 3.5, "B", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(2.25, 2.25, "∩", ha="center", va="center", fontsize=14, fontweight="bold")
    ax.set_xlim(-0.5, 5)
    ax.set_ylim(-0.5, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("IoU ≈ 0.14\n(częściowe nakładanie)", fontsize=FS, fontweight="bold")

    # High IoU
    ax = axes[2]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 3, 3, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    ax.add_patch(
        mpatches.Rectangle(
            (0.3, 0.3), 3, 3, facecolor=GRAY2, edgecolor=LN, lw=1.5, alpha=0.7
        )
    )
    ax.add_patch(
        mpatches.Rectangle((0.3, 0.3), 2.7, 2.7, facecolor=GRAY3, edgecolor=LN, lw=2)
    )
    ax.text(-0.3, -0.3, "A", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(3.5, 3.5, "B", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(1.65, 1.65, "∩", ha="center", va="center", fontsize=14, fontweight="bold")
    ax.set_xlim(-0.8, 4)
    ax.set_ylim(-0.8, 4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "IoU ≈ 0.74\n(duże nakładanie → duplikat!)", fontsize=FS, fontweight="bold"
    )

    fig.tight_layout()
    save_fig(fig, "q24_iou_diagram.png")


# ============================================================
# 9. NMS Step-by-Step
# ============================================================
def draw_nms_steps() -> None:
    """Draw nms steps."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle(
        "NMS (Non-Maximum Suppression) — usuwanie duplikatów",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Before NMS
    ax = axes[0]
    ax.add_patch(mpatches.Rectangle((0, 0), 6, 5, facecolor=GRAY4, edgecolor=LN, lw=1))
    # Multiple overlapping boxes for same object
    ax.add_patch(
        mpatches.Rectangle((1, 1), 2.5, 3, facecolor="none", edgecolor=LN, lw=2)
    )
    ax.text(2.25, 4.2, "conf=0.95", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.add_patch(
        mpatches.Rectangle(
            (1.2, 1.3), 2.3, 2.8, facecolor="none", edgecolor=LN, lw=1.5, linestyle="--"
        )
    )
    ax.text(2.35, 1.1, "conf=0.90", ha="center", fontsize=FS_SMALL)
    ax.add_patch(
        mpatches.Rectangle(
            (0.8, 0.8), 2.7, 3.2, facecolor="none", edgecolor=LN, lw=1, linestyle=":"
        )
    )
    ax.text(2.15, 0.6, "conf=0.85", ha="center", fontsize=FS_SMALL)
    # Different object
    ax.add_patch(
        mpatches.Rectangle((4, 2), 1.5, 1.5, facecolor="none", edgecolor=LN, lw=1.5)
    )
    ax.text(4.75, 3.7, "conf=0.80", ha="center", fontsize=FS_SMALL)
    ax.text(
        2,
        0.2,
        "⚠ 4 detekcje (3 duplikaty!)",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    ax.set_xlim(-0.3, 6.3)
    ax.set_ylim(-0.3, 5.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "① Przed NMS\n(wiele nakładających się)", fontsize=FS, fontweight="bold"
    )

    # NMS process
    ax = axes[1]
    ax.axis("off")
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 5)

    steps = [
        ("1. Sortuj: [0.95, 0.90, 0.85, 0.80]", 4.5),
        ("2. Weź najlepszą (0.95) → ZACHOWAJ", 3.7),
        ("3. IoU(0.95, 0.90)=0.82 > 0.5 → USUŃ", 2.9),
        ("4. IoU(0.95, 0.85)=0.75 > 0.5 → USUŃ", 2.1),
        ("5. IoU(0.95, 0.80)=0.10 < 0.5 → ZACHOWAJ", 1.3),
    ]
    colors = [GRAY4, GRAY2, GRAY4, GRAY4, GRAY2]
    for (text, yp), c in zip(steps, colors, strict=False):
        ax.text(
            3.0,
            yp,
            text,
            ha="center",
            fontsize=FS,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": c, "edgecolor": GRAY3},
        )

    ax.set_title("② Algorytm NMS\n(próg IoU = 0.5)", fontsize=FS, fontweight="bold")

    # After NMS
    ax = axes[2]
    ax.add_patch(mpatches.Rectangle((0, 0), 6, 5, facecolor=GRAY4, edgecolor=LN, lw=1))
    # Only best box for each object
    ax.add_patch(
        mpatches.Rectangle((1, 1), 2.5, 3, facecolor="none", edgecolor=LN, lw=2.5)
    )
    ax.text(2.25, 4.2, "conf=0.95 ✓", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.add_patch(
        mpatches.Rectangle((4, 2), 1.5, 1.5, facecolor="none", edgecolor=LN, lw=2.5)
    )
    ax.text(4.75, 3.7, "conf=0.80 ✓", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.text(
        3,
        0.2,
        "✓ 2 unikalne obiekty",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    ax.set_xlim(-0.3, 6.3)
    ax.set_ylim(-0.3, 5.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("③ Po NMS\n(1 bbox na obiekt)", fontsize=FS, fontweight="bold")

    fig.tight_layout()
    save_fig(fig, "q24_nms_steps.png")


# ============================================================
# 10. Detector from Classifier — 3 approaches
# ============================================================
def draw_detector_from_classifier() -> None:
    """Draw detector from classifier."""
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_xlim(-0.5, 11)
    ax.set_ylim(-1, 9.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Jak zbudować detektor z klasyfikatora? — 3 podejścia",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    # ---- Approach 1: Sliding Window ----
    y = 7.0
    ax.text(
        0,
        y + 1.5,
        "① Sliding Window (NAJWOLNIEJSZE)",
        fontsize=FS_LABEL,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # Image with sliding window
    ax.add_patch(
        mpatches.Rectangle(
            (0, y - 0.6), 1.8, 1.8, facecolor=GRAY1, edgecolor=LN, lw=1.5
        )
    )
    ax.text(0.9, y + 0.3, "obraz", ha="center", fontsize=FS_SMALL)
    # Sliding windows
    for dx, dy in [(0.1, 0.1), (0.4, 0.1), (0.7, 0.1), (0.1, 0.5), (0.4, 0.5)]:
        ax.add_patch(
            mpatches.Rectangle(
                (dx, y - 0.5 + dy),
                0.5,
                0.5,
                facecolor="none",
                edgecolor=LN,
                lw=0.8,
                linestyle="--",
            )
        )

    draw_arrow(ax, 2.0, y + 0.3, 2.7, y + 0.3, lw=1.2)
    ax.text(2.35, y + 0.6, "xmiliony", fontsize=FS_SMALL, style="italic")

    draw_box(
        ax,
        2.8,
        y - 0.3,
        1.8,
        1.2,
        'Klasyfikator\n(ResNet)\n"kot? pies? tło?"',
        fill=GRAY4,
        fontsize=FS,
    )
    draw_arrow(ax, 4.7, y + 0.3, 5.3, y + 0.3, lw=1.2)
    draw_box(ax, 5.4, y - 0.3, 1.2, 1.2, "NMS", fill=GRAY1, fontsize=FS)
    draw_arrow(ax, 6.7, y + 0.3, 7.3, y + 0.3, lw=1.2)
    ax.text(
        8.5,
        y + 0.3,
        "~3.3h / obraz!\n⚠ NIEPRAKTYCZNE",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # ---- Approach 2: Region Proposals ----
    y = 3.8
    ax.text(
        0,
        y + 1.5,
        "② Region Proposals + Klasyfikator (= R-CNN)",
        fontsize=FS_LABEL,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.add_patch(
        mpatches.Rectangle(
            (0, y - 0.6), 1.8, 1.8, facecolor=GRAY1, edgecolor=LN, lw=1.5
        )
    )
    ax.text(0.9, y + 0.3, "obraz", ha="center", fontsize=FS_SMALL)
    # A few smart regions
    ax.add_patch(
        mpatches.Rectangle(
            (0.1, y - 0.4), 0.7, 0.9, facecolor="none", edgecolor=LN, lw=1.5
        )
    )
    ax.add_patch(
        mpatches.Rectangle(
            (0.9, y + 0.0), 0.7, 0.6, facecolor="none", edgecolor=LN, lw=1.5
        )
    )

    draw_arrow(ax, 2.0, y + 0.3, 2.7, y + 0.3, lw=1.2)
    draw_box(
        ax,
        2.8,
        y - 0.3,
        1.6,
        1.2,
        "Selective\nSearch\n~2000 regionów",
        fill=GRAY2,
        fontsize=FS,
    )
    draw_arrow(ax, 4.5, y + 0.3, 5.1, y + 0.3, lw=1.2)
    ax.text(4.8, y + 0.6, "x2000", fontsize=FS_SMALL, style="italic")
    draw_box(ax, 5.2, y - 0.3, 1.5, 1.2, "Klasyfikator\n(CNN)", fill=GRAY4, fontsize=FS)
    draw_arrow(ax, 6.8, y + 0.3, 7.4, y + 0.3, lw=1.2)
    draw_box(ax, 7.5, y - 0.3, 1.0, 1.2, "NMS", fill=GRAY1, fontsize=FS)
    draw_arrow(ax, 8.6, y + 0.3, 9.0, y + 0.3, lw=1.2)
    ax.text(
        10.0,
        y + 0.3,
        "~20-50 s/obraz\n(250x szybciej)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # ---- Approach 3: Fine-tune backbone ----
    y = 0.5
    ax.text(
        0,
        y + 1.5,
        "③ Fine-tune backbone + detection head (NAJLEPSZE)",
        fontsize=FS_LABEL,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY2, "edgecolor": GRAY3},
    )

    ax.add_patch(
        mpatches.Rectangle(
            (0, y - 0.6), 1.8, 1.8, facecolor=GRAY1, edgecolor=LN, lw=1.5
        )
    )
    ax.text(0.9, y + 0.3, "obraz", ha="center", fontsize=FS_SMALL)

    draw_arrow(ax, 2.0, y + 0.3, 2.7, y + 0.3, lw=1.2)
    draw_box(
        ax,
        2.8,
        y - 0.3,
        1.8,
        1.2,
        "Pretrained\nbackbone\n(ResNet)",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 4.7, y + 0.3, 5.3, y + 0.3, lw=1.2)

    # Two heads from feature map
    draw_box(ax, 5.4, y + 0.3, 1.6, 0.6, "cls head\nP(klasa)", fill=GRAY4, fontsize=FS)
    draw_box(
        ax, 5.4, y - 0.5, 1.6, 0.6, "bbox head\nΔx,Δy,Δw,Δh", fill=GRAY4, fontsize=FS
    )

    draw_arrow(ax, 7.1, y + 0.6, 7.7, y + 0.6, lw=1.0)
    draw_arrow(ax, 7.1, y - 0.2, 7.7, y - 0.2, lw=1.0)
    draw_box(ax, 7.8, y - 0.3, 1.0, 1.2, "NMS", fill=GRAY1, fontsize=FS)

    draw_arrow(ax, 8.9, y + 0.3, 9.3, y + 0.3, lw=1.2)
    ax.text(
        10.2,
        y + 0.3,
        "5-155 fps!\n✓ NAJLEPSZE",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY2, "edgecolor": GRAY3},
    )

    save_fig(fig, "q24_detector_from_classifier.png")
