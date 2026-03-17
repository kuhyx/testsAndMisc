"""Vision and statistics diagrams (HOG, R-CNN, segmentation, FSD/SSD)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from python_pkg.praca_magisterska_video.generate_images.generate_study_diagrams import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    OUTPUT_DIR,
    draw_arrow,
    draw_box,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
from pathlib import Path

_logger = logging.getLogger(__name__)


def draw_hog_pipeline() -> None:
    """Draw hog pipeline."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_title(
        "HOG + SVM — pipeline detekcji pieszych",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    steps = [
        (0.3, "Obraz\nwejściowy", GRAY4),
        (2.1, "Oblicz\ngradienty\n(Gx, Gy)", GRAY1),
        (3.9, "Podziel na\nkomórki 8x8\nhistogramy", GRAY2),
        (5.7, "Normalizuj\nw blokach\n2x2", GRAY2),
        (7.5, "Wektor\ncech\n(3780-dim)", GRAY3),
        (9.0, "SVM\n→ pieszy\n/ nie", GRAY1),
    ]

    box_w = 1.5
    box_h = 1.8
    y = 1.2
    for i, (x, text, fill) in enumerate(steps):
        draw_box(ax, x, y, box_w, box_h, "", fill=fill)
        ax.text(
            x + box_w / 2, y + box_h / 2, text, ha="center", va="center", fontsize=7
        )
        if i < len(steps) - 1:
            next_x = steps[i + 1][0]
            draw_arrow(
                ax, x + box_w + 0.02, y + box_h / 2, next_x - 0.02, y + box_h / 2
            )

    # Annotations below
    annotations = [
        (0.3 + box_w / 2, "pixel[x+1]-pixel[x-1]"),
        (2.1 + box_w / 2, "magnitude + direction"),
        (3.9 + box_w / 2, "9 binów (0°-180°)"),
        (5.7 + box_w / 2, "L2-normalizacja"),
        (7.5 + box_w / 2, "wejście do SVM"),
        (9.0 + box_w / 2, "hiperpłaszczyzna"),
    ]
    for x, text in annotations:
        ax.text(
            x,
            y - 0.15,
            text,
            ha="center",
            fontsize=5.5,
            color="#666666",
            style="italic",
        )

    # Title annotations
    ax.text(
        1.05, y + box_h + 0.15, "① Gradient", ha="center", fontsize=7, fontweight="bold"
    )
    ax.text(
        2.85,
        y + box_h + 0.15,
        "② Histogram",
        ha="center",
        fontsize=7,
        fontweight="bold",
    )
    ax.text(
        4.65,
        y + box_h + 0.15,
        "③ Normalize",
        ha="center",
        fontsize=7,
        fontweight="bold",
    )
    ax.text(
        6.45,
        y + box_h + 0.15,
        "④ Feature vec",
        ha="center",
        fontsize=7,
        fontweight="bold",
    )
    ax.text(
        8.1, y + box_h + 0.15, "⑤ Classify", ha="center", fontsize=7, fontweight="bold"
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "hog_svm_pipeline.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ hog_svm_pipeline.png")


def draw_rcnn_evolution() -> None:
    """Draw rcnn evolution."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title(
        "Ewolucja detektorów: R-CNN → Fast R-CNN → Faster R-CNN → YOLO",
        fontsize=10,
        fontweight="bold",
        pad=10,
    )

    models = [
        {
            "name": "R-CNN (2014)",
            "y": 5.3,
            "steps": ["Selective\nSearch", "2000x\nCNN", "2000x\nSVM", "NMS"],
            "speed": "~50 sec/img",
            "fill": GRAY4,
        },
        {
            "name": "Fast R-CNN (2015)",
            "y": 3.7,
            "steps": [
                "Selective\nSearch",
                "CNN\n(1x cały)",
                "ROI\nPooling",
                "FC + NMS",
            ],
            "speed": "~2 sec/img",
            "fill": GRAY2,
        },
        {
            "name": "Faster R-CNN (2015)",
            "y": 2.1,
            "steps": ["CNN\nbackbone", "RPN\n(proposals)", "ROI\nPooling", "FC + NMS"],
            "speed": "~0.2 sec (5 fps)",
            "fill": GRAY1,
        },
        {
            "name": "YOLO (2016)",
            "y": 0.5,
            "steps": ["CNN\nbackbone", "Siatka\nSxS", "bbox+klasa\nper komórka", "NMS"],
            "speed": "~7-22 ms (45-155 fps)",
            "fill": GRAY3,
        },
    ]

    for model in models:
        y = model["y"]
        ax.text(0.2, y + 0.4, model["name"], fontsize=8, fontweight="bold", va="center")
        ax.text(0.2, y + 0.05, model["speed"], fontsize=6, va="center", color="#666666")

        bw = 1.5
        bh = 0.8
        for i, step in enumerate(model["steps"]):
            x = 2.5 + i * 1.9
            draw_box(ax, x, y, bw, bh, step, fill=model["fill"], fontsize=6.5)
            if i < len(model["steps"]) - 1:
                draw_arrow(
                    ax, x + bw + 0.02, y + bh / 2, x + 1.9 - 0.02, y + bh / 2, lw=0.8
                )

    # Speed improvement arrow on right
    ax.annotate(
        "",
        xy=(9.5, 5.7),
        xytext=(9.5, 0.9),
        arrowprops={"arrowstyle": "<->", "color": "#555555", "lw": 1.5},
    )
    ax.text(
        9.7,
        3.3,
        "250x\nszybciej!",
        fontsize=8,
        fontweight="bold",
        ha="center",
        va="center",
        rotation=90,
        color="#555555",
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "rcnn_evolution.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ rcnn_evolution.png")


def _draw_instance_panel(ax: Axes) -> None:
    """Draw instance segmentation panel."""
    ax.add_patch(
        mpatches.Rectangle((0, 4), 6, 2, facecolor="#E8E8E8", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 5, "\u2014", ha="center", va="center", fontsize=7, color="#999999")
    ax.add_patch(
        mpatches.Rectangle((0, 0), 6, 2.5, facecolor="#E8E8E8", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 1, "\u2014", ha="center", va="center", fontsize=7, color="#999999")
    ax.add_patch(
        mpatches.Rectangle((0.5, 2), 2, 1.5, facecolor="#888888", edgecolor=LN, lw=0.8)
    )
    ax.text(1.5, 2.75, "auto#1", ha="center", va="center", fontsize=6, color="white")
    ax.add_patch(
        mpatches.Rectangle((3.5, 2), 2, 1.5, facecolor="#555555", edgecolor=LN, lw=0.8)
    )
    ax.text(4.5, 2.75, "auto#2", ha="center", va="center", fontsize=6, color="white")
    ax.text(
        3,
        -0.3,
        "RÓŻNE instancje!",
        ha="center",
        fontsize=6,
        color="#555555",
        style="italic",
    )


def _draw_panoptic_panel(ax: Axes) -> None:
    """Draw panoptic segmentation panel."""
    ax.add_patch(
        mpatches.Rectangle((0, 4), 6, 2, facecolor="#E8E8E8", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 5, "niebo (stuff)", ha="center", va="center", fontsize=6)
    ax.add_patch(
        mpatches.Rectangle((0, 0), 6, 2.5, facecolor="#C8C8C8", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 1, "droga (stuff)", ha="center", va="center", fontsize=6)
    ax.add_patch(
        mpatches.Rectangle((0.5, 2), 2, 1.5, facecolor="#888888", edgecolor=LN, lw=0.8)
    )
    ax.text(
        1.5,
        2.75,
        "auto#1\n(thing)",
        ha="center",
        va="center",
        fontsize=5.5,
        color="white",
    )
    ax.add_patch(
        mpatches.Rectangle((3.5, 2), 2, 1.5, facecolor="#555555", edgecolor=LN, lw=0.8)
    )
    ax.text(
        4.5,
        2.75,
        "auto#2\n(thing)",
        ha="center",
        va="center",
        fontsize=5.5,
        color="white",
    )
    ax.text(
        3,
        -0.3,
        "klasy + instancje!",
        ha="center",
        fontsize=6,
        color="#555555",
        style="italic",
    )


def draw_segmentation_types() -> None:
    """Draw segmentation types."""
    fig, axes = plt.subplots(1, 4, figsize=(8.27, 2.5))
    fig.suptitle(
        "Typy segmentacji obrazu", fontsize=FS_TITLE, fontweight="bold", y=1.02
    )

    titles = [
        "Obraz wejściowy",
        "Semantic\nSegmentation",
        "Instance\nSegmentation",
        "Panoptic\nSegmentation",
    ]
    for ax, title in zip(axes, titles, strict=False):
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=8, fontweight="bold", pad=5)

    # Original image (stylized)
    ax = axes[0]
    ax.add_patch(
        mpatches.Rectangle((0, 4), 6, 2, facecolor="#DDDDDD", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 5, "niebo", ha="center", va="center", fontsize=7)
    ax.add_patch(
        mpatches.Rectangle((0, 0), 6, 2.5, facecolor="#AAAAAA", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 1, "droga", ha="center", va="center", fontsize=7)
    ax.add_patch(
        mpatches.Rectangle((0.5, 2), 2, 1.5, facecolor="#888888", edgecolor=LN, lw=0.8)
    )
    ax.text(1.5, 2.75, "auto", ha="center", va="center", fontsize=7, color="white")
    ax.add_patch(
        mpatches.Rectangle((3.5, 2), 2, 1.5, facecolor="#666666", edgecolor=LN, lw=0.8)
    )
    ax.text(4.5, 2.75, "auto", ha="center", va="center", fontsize=7, color="white")

    # Semantic: same label for both cars
    ax = axes[1]
    ax.add_patch(
        mpatches.Rectangle((0, 4), 6, 2, facecolor="#E8E8E8", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 5, "niebo", ha="center", va="center", fontsize=7)
    ax.add_patch(
        mpatches.Rectangle((0, 0), 6, 2.5, facecolor="#C8C8C8", edgecolor=LN, lw=0.5)
    )
    ax.text(3, 1, "droga", ha="center", va="center", fontsize=7)
    ax.add_patch(
        mpatches.Rectangle((0.5, 2), 2, 1.5, facecolor="#888888", edgecolor=LN, lw=0.8)
    )
    ax.text(1.5, 2.75, "auto", ha="center", va="center", fontsize=6, color="white")
    ax.add_patch(
        mpatches.Rectangle((3.5, 2), 2, 1.5, facecolor="#888888", edgecolor=LN, lw=0.8)
    )
    ax.text(4.5, 2.75, "auto", ha="center", va="center", fontsize=6, color="white")
    ax.text(
        3,
        -0.3,
        "te same etykiety!",
        ha="center",
        fontsize=6,
        color="#555555",
        style="italic",
    )

    _draw_instance_panel(axes[2])
    _draw_panoptic_panel(axes[3])

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "segmentation_types.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ segmentation_types.png")


def draw_fsd_ssd() -> None:
    """Draw fsd ssd."""
    fig, axes = plt.subplots(1, 2, figsize=(8.27, 3.5))
    fig.suptitle(
        "Dominacja stochastyczna — FSD i SSD",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # FSD: CDF comparison
    ax = axes[0]
    ax.set_title("FSD: F_A(x) ≤ F_B(x) ∀x", fontsize=9, fontweight="bold")
    x = np.linspace(-2, 6, 200)
    cdf_a = norm.cdf(x, loc=2.5, scale=1.0)
    cdf_b = norm.cdf(x, loc=1.5, scale=1.0)
    ax.plot(x, cdf_a, "k-", lw=2, label="F_A (lepsza — niżej)")
    ax.plot(x, cdf_b, "k--", lw=2, label="F_B (gorsza — wyżej)")
    ax.fill_between(x, cdf_a, cdf_b, alpha=0.15, color="gray")
    ax.set_xlabel("x (wynik)", fontsize=8)
    ax.set_ylabel("F(x) = P(X ≤ x)", fontsize=8)
    ax.legend(fontsize=7, loc="lower right")
    ax.text(
        0,
        0.8,
        "A ≥_FSD B\nF_A zawsze pod F_B\n→ KAŻDY racjonalny\n   wybierze A",
        fontsize=7,
        bbox={"boxstyle": "round", "facecolor": GRAY4},
    )
    ax.grid(visible=True, alpha=0.3)
    ax.tick_params(labelsize=7)

    # SSD
    ax = axes[1]
    ax.set_title(
        "SSD: ∫F_A ≤ ∫F_B ∀x (CDFs mogą się krzyżować)", fontsize=9, fontweight="bold"
    )
    cdf_a2 = norm.cdf(x, loc=2.0, scale=0.8)
    cdf_b2 = norm.cdf(x, loc=2.0, scale=1.5)
    ax.plot(x, cdf_a2, "k-", lw=2, label="F_A (mniej ryzyka)")
    ax.plot(x, cdf_b2, "k--", lw=2, label="F_B (więcej ryzyka)")
    ax.fill_between(x, cdf_a2, cdf_b2, where=cdf_a2 < cdf_b2, alpha=0.15, color="gray")
    ax.fill_between(
        x, cdf_a2, cdf_b2, where=cdf_a2 >= cdf_b2, alpha=0.08, color="gray", hatch="///"
    )
    ax.set_xlabel("x (wynik)", fontsize=8)
    ax.set_ylabel("F(x)", fontsize=8)
    ax.legend(fontsize=7, loc="lower right")
    ax.text(
        -1.5,
        0.75,
        "A ≥_SSD B\nCDFs się krzyżują,\nale ∫F_A ≤ ∫F_B\n→ risk-averse\n   wybierze A",
        fontsize=7,
        bbox={"boxstyle": "round", "facecolor": GRAY4},
    )
    ax.grid(visible=True, alpha=0.3)
    ax.tick_params(labelsize=7)

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "fsd_ssd_comparison.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ fsd_ssd_comparison.png")
