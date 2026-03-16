"""Haar features, integral image, and SVM hyperplane diagrams."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q24_common import (
    _DATA_BRIGHT_THRESH,
    _II_BRIGHT_THRESH,
    FS,
    FS_LABEL,
    FS_SMALL,
    FS_TITLE,
    GRAY3,
    GRAY4,
    LN,
    np,
    plt,
    rng,
    save_fig,
)
import matplotlib.patches as mpatches

if TYPE_CHECKING:
    from matplotlib.axes import Axes


# ============================================================
# 4. Haar Features
# ============================================================
def draw_haar_features() -> None:
    """Draw haar features."""
    fig, axes = plt.subplots(1, 4, figsize=(11, 3))
    fig.suptitle(
        "Cechy Haar — typy i zastosowanie na twarzy",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Feature 1: Vertical edge
    ax = axes[0]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 1, 2, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    ax.add_patch(
        mpatches.Rectangle((1, 0), 1, 2, facecolor=GRAY3, edgecolor=LN, lw=1.5)
    )
    ax.text(
        0.5, 1, "+Σ₁", ha="center", va="center", fontsize=FS_LABEL, fontweight="bold"
    )
    ax.text(
        1.5, 1, "-Σ₂", ha="center", va="center", fontsize=FS_LABEL, fontweight="bold"
    )
    ax.set_xlim(-0.2, 2.2)
    ax.set_ylim(-0.5, 2.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Krawędź pionowa\nwartość = Σ₁ - Σ₂", fontsize=FS)

    # Feature 2: Horizontal edge
    ax = axes[1]
    ax.add_patch(
        mpatches.Rectangle((0, 1), 2, 1, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    ax.add_patch(
        mpatches.Rectangle((0, 0), 2, 1, facecolor=GRAY3, edgecolor=LN, lw=1.5)
    )
    ax.text(
        1, 1.5, "+Σ₁", ha="center", va="center", fontsize=FS_LABEL, fontweight="bold"
    )
    ax.text(
        1, 0.5, "-Σ₂", ha="center", va="center", fontsize=FS_LABEL, fontweight="bold"
    )
    ax.set_xlim(-0.2, 2.2)
    ax.set_ylim(-0.5, 2.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Krawędź pozioma\n(oczy vs czoło)", fontsize=FS)

    # Feature 3: Three-rectangle (line)
    ax = axes[2]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 0.7, 2, facecolor=GRAY3, edgecolor=LN, lw=1.5)
    )
    ax.add_patch(
        mpatches.Rectangle((0.7, 0), 0.7, 2, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    ax.add_patch(
        mpatches.Rectangle((1.4, 0), 0.7, 2, facecolor=GRAY3, edgecolor=LN, lw=1.5)
    )
    ax.text(
        0.35, 1, "-Σ₁", ha="center", va="center", fontsize=FS_SMALL, fontweight="bold"
    )
    ax.text(
        1.05, 1, "+Σ₂", ha="center", va="center", fontsize=FS_SMALL, fontweight="bold"
    )
    ax.text(
        1.75, 1, "-Σ₃", ha="center", va="center", fontsize=FS_SMALL, fontweight="bold"
    )
    ax.set_xlim(-0.2, 2.3)
    ax.set_ylim(-0.5, 2.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Linia (3 prostokąty)\n(nos vs policzki)", fontsize=FS)

    _draw_haar_face_panel(axes[3])

    fig.tight_layout()
    save_fig(fig, "q24_haar_features.png")


def _draw_haar_face_panel(ax: Axes) -> None:
    """Draw Haar feature application on face schematic."""
    face = mpatches.Ellipse(
        (1.2, 1.2),
        2.0,
        2.4,
        facecolor=GRAY4,
        edgecolor=LN,
        lw=1.5,
    )
    ax.add_patch(face)
    ax.add_patch(
        mpatches.Ellipse((0.7, 1.6), 0.4, 0.2, facecolor=GRAY3, edgecolor=LN, lw=1)
    )
    ax.add_patch(
        mpatches.Ellipse((1.7, 1.6), 0.4, 0.2, facecolor=GRAY3, edgecolor=LN, lw=1)
    )
    ax.plot([1.2, 1.1, 1.3], [1.3, 0.9, 0.9], color=LN, lw=1)
    ax.plot([0.8, 1.0, 1.2, 1.4, 1.6], [0.55, 0.5, 0.55, 0.5, 0.55], color=LN, lw=1)
    ax.add_patch(
        mpatches.Rectangle(
            (0.3, 1.4),
            1.8,
            0.4,
            facecolor="none",
            edgecolor=LN,
            lw=2,
            linestyle="--",
        )
    )
    ax.annotate(
        "cechy Haar\n(oczy ciemne\nvs czoło jasne)",
        xy=(1.2, 1.85),
        xytext=(2.2, 2.3),
        fontsize=FS_SMALL,
        ha="center",
        arrowprops={"arrowstyle": "->", "color": LN, "lw": 1},
    )
    ax.set_xlim(-0.2, 3.0)
    ax.set_ylim(-0.2, 2.8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Zastosowanie na twarzy", fontsize=FS)


# ============================================================
# 5. Integral Image
# ============================================================
def draw_integral_image() -> None:
    """Draw integral image."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
    fig.suptitle(
        "Integral Image — suma prostokąta w O(1)",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Original image
    ax = axes[0]
    data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    ax.imshow(data, cmap="gray", vmin=0, vmax=10)
    for i in range(3):
        for j in range(3):
            ax.text(
                j,
                i,
                str(data[i, j]),
                ha="center",
                va="center",
                fontsize=12,
                fontweight="bold",
                color="white" if data[i, j] > _DATA_BRIGHT_THRESH else "black",
            )
    ax.set_title("① Obraz oryginalny", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Integral image
    ax = axes[1]
    ii = np.array([[1, 3, 6], [5, 12, 21], [12, 27, 45]])
    ax.imshow(ii, cmap="gray", vmin=0, vmax=50)
    for i in range(3):
        for j in range(3):
            ax.text(
                j,
                i,
                str(ii[i, j]),
                ha="center",
                va="center",
                fontsize=12,
                fontweight="bold",
                color="white" if ii[i, j] > _II_BRIGHT_THRESH else "black",
            )
    ax.set_title("② Integral Image\n(sumy kumulatywne)", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Formula illustration
    ax = axes[2]
    ax.axis("off")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    # Draw rectangle
    ax.add_patch(
        mpatches.Rectangle((0.5, 0.5), 3, 3, facecolor="white", edgecolor=LN, lw=1)
    )
    ax.add_patch(
        mpatches.Rectangle((1.5, 0.5), 2, 2, facecolor=GRAY3, edgecolor=LN, lw=2)
    )
    # Labels
    ax.text(0.3, 3.7, "A", fontsize=12, fontweight="bold")
    ax.text(3.6, 3.7, "B", fontsize=12, fontweight="bold")
    ax.text(0.3, 0.3, "C", fontsize=12, fontweight="bold")
    ax.text(3.6, 0.3, "D", fontsize=12, fontweight="bold")
    ax.text(
        2.5,
        1.5,
        "SZUKANA\nSUMA",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
    )
    ax.text(
        2.0,
        -0.3,
        "Suma = D - B - C + A\n= 4 odczyty → O(1) ZAWSZE!",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )
    ax.set_title(
        "③ Formuła: 4 odczyty\n= O(1) niezależnie od rozmiaru",
        fontsize=FS,
        fontweight="bold",
    )

    fig.tight_layout()
    save_fig(fig, "q24_integral_image.png")


# ============================================================
# 11. SVM Hyperplane
# ============================================================
def draw_svm_hyperplane() -> None:
    """Draw svm hyperplane."""
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_title(
        "SVM — hiperpłaszczyzna i margines",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    x_pos = rng.standard_normal(15) * 0.5 + 3
    y_pos = rng.standard_normal(15) * 0.5 + 3
    ax.scatter(
        x_pos,
        y_pos,
        marker="o",
        s=50,
        facecolors="white",
        edgecolors=LN,
        linewidths=1.5,
        label="klasa +1 (pieszy)",
        zorder=3,
    )

    x_neg = rng.standard_normal(15) * 0.5 + 1
    y_neg = rng.standard_normal(15) * 0.5 + 1
    ax.scatter(
        x_neg,
        y_neg,
        marker="x",
        s=50,
        c=LN,
        linewidths=1.5,
        label="klasa -1 (tło)",
        zorder=3,
    )

    # Hyperplane (decision boundary)
    x_line = np.linspace(-0.5, 5, 100)
    y_line = -x_line + 4.0
    ax.plot(x_line, y_line, "k-", lw=2, label="hiperpłaszczyzna")

    # Margin lines
    ax.plot(x_line, y_line + 0.7, "k--", lw=1, alpha=0.5)
    ax.plot(x_line, y_line - 0.7, "k--", lw=1, alpha=0.5)

    # Margin annotation
    ax.annotate(
        "",
        xy=(2.5, 1.5 + 0.7),
        xytext=(2.5, 1.5 - 0.7),
        arrowprops={"arrowstyle": "<->", "color": LN, "lw": 1.5},
    )
    ax.text(2.8, 1.5, "margines\n(MAX!)", fontsize=FS, fontweight="bold")

    # Support vectors (highlight closest points)
    ax.scatter(
        [2.5],
        [2.2],
        marker="o",
        s=120,
        facecolors="none",
        edgecolors=LN,
        linewidths=2.5,
        zorder=4,
    )
    ax.scatter([1.5], [1.8], marker="x", s=120, c=LN, linewidths=2.5, zorder=4)
    ax.annotate(
        "support\nvectors",
        xy=(1.5, 1.8),
        xytext=(0.2, 3.0),
        fontsize=FS,
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "color": LN, "lw": 1},
    )

    ax.set_xlim(-0.5, 5)
    ax.set_ylim(-0.5, 5)
    ax.set_xlabel("cecha 1 (np. gradient pionowy)", fontsize=FS)
    ax.set_ylabel("cecha 2 (np. gradient poziomy)", fontsize=FS)
    ax.legend(fontsize=FS_SMALL, loc="lower right")
    ax.set_aspect("equal")

    save_fig(fig, "q24_svm_hyperplane.png")
