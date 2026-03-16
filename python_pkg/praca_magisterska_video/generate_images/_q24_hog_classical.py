"""HOG + SVM pipeline, HOG gradient steps, Viola-Jones cascade."""

from __future__ import annotations

from _q24_common import (
    _DOTS_STAGE_IDX,
    _GRADIENT_BRIGHT_THRESH,
    _PIXEL_BRIGHT_THRESH,
    FS,
    FS_LABEL,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    draw_arrow,
    draw_box,
    np,
    plt,
    save_fig,
)
import matplotlib.patches as mpatches


# ============================================================
# 1. HOG + SVM Pipeline
# ============================================================
def draw_hog_svm_pipeline() -> None:
    """Draw hog svm pipeline."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-1, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "HOG + SVM — pipeline detekcji pieszych",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    # Step 1: Image with sliding window
    ax.add_patch(
        mpatches.Rectangle((0, 1.5), 2, 2, lw=1.5, edgecolor=LN, facecolor=GRAY1)
    )
    ax.text(1, 2.5, "Obraz\nwejściowy", ha="center", va="center", fontsize=FS)
    # sliding window overlay
    ax.add_patch(
        mpatches.Rectangle(
            (0.3, 1.8),
            0.8,
            1.2,
            lw=1.5,
            edgecolor="black",
            facecolor="none",
            linestyle="--",
        )
    )
    ax.text(
        0.7,
        1.35,
        "okno 64x128",
        ha="center",
        va="center",
        fontsize=FS_SMALL,
        style="italic",
    )

    draw_arrow(ax, 2.1, 2.5, 2.8, 2.5, lw=1.5)
    ax.text(2.45, 2.75, "①", ha="center", fontsize=FS_LABEL, fontweight="bold")

    # Step 2: Gradient computation
    draw_box(
        ax, 2.9, 1.8, 1.6, 1.4, "Oblicz\ngradienty\nGx, Gy", fill=GRAY4, fontsize=FS
    )
    ax.text(
        3.7, 1.55, "kierunek + siła", ha="center", fontsize=FS_SMALL, style="italic"
    )

    draw_arrow(ax, 4.6, 2.5, 5.2, 2.5, lw=1.5)
    ax.text(4.9, 2.75, "②", ha="center", fontsize=FS_LABEL, fontweight="bold")

    # Step 3: HOG histogram
    draw_box(
        ax,
        5.3,
        1.8,
        1.6,
        1.4,
        "Histogramy\nkierunkowe\n9 binów/cel",
        fill=GRAY4,
        fontsize=FS,
    )
    ax.text(6.1, 1.55, "komórki 8x8 px", ha="center", fontsize=FS_SMALL, style="italic")

    draw_arrow(ax, 7.0, 2.5, 7.6, 2.5, lw=1.5)
    ax.text(7.3, 2.75, "③", ha="center", fontsize=FS_LABEL, fontweight="bold")

    # Step 4: SVM
    draw_box(
        ax,
        7.7,
        1.8,
        1.4,
        1.4,
        "SVM\nklasyfikator\npieszy/tło",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )

    draw_arrow(ax, 9.2, 2.5, 9.7, 2.5, lw=1.5)
    ax.text(9.45, 2.75, "④", ha="center", fontsize=FS_LABEL, fontweight="bold")

    # Step 5: NMS + output
    draw_box(ax, 9.3, 2.0, 1.0, 1.0, "NMS\n→ wynik", fill=GRAY1, fontsize=FS)

    # Bottom: HOG feature vector illustration
    ax.text(
        5.0,
        0.7,
        "Wektor HOG: 3780 cech = 105 bloków x 4 komórki x 9 binów",
        ha="center",
        fontsize=FS,
        style="italic",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    # Show small histogram bars
    bar_x = 3.2
    bar_y = 0.0
    angles = [0, 20, 40, 60, 80, 100, 120, 140, 160]
    values = [0.3, 0.1, 0.5, 0.8, 0.2, 0.6, 0.15, 0.4, 0.25]
    for i, (_a, v) in enumerate(zip(angles, values, strict=False)):
        ax.add_patch(
            mpatches.Rectangle(
                (bar_x + i * 0.18, bar_y),
                0.15,
                v * 0.6,
                facecolor=GRAY3,
                edgecolor=LN,
                lw=0.5,
            )
        )
    ax.text(bar_x + 0.8, -0.2, "9 binów (0°-160°)", ha="center", fontsize=FS_SMALL)

    save_fig(fig, "q24_hog_svm_pipeline.png")


# ============================================================
# 2. HOG Gradient Step-by-Step
# ============================================================
def draw_hog_gradient_steps() -> None:
    """Draw hog gradient steps."""
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.5))
    fig.suptitle(
        "HOG — kroki obliczania cech", fontsize=FS_TITLE, fontweight="bold", y=1.02
    )

    # Step 1: Original patch
    ax = axes[0]
    patch = np.array([[50, 50, 200], [50, 50, 200], [50, 50, 200]])
    ax.imshow(patch, cmap="gray", vmin=0, vmax=255)
    for i in range(3):
        for j in range(3):
            ax.text(
                j,
                i,
                str(patch[i, j]),
                ha="center",
                va="center",
                fontsize=FS_LABEL,
                fontweight="bold",
                color="white" if patch[i, j] > _PIXEL_BRIGHT_THRESH else "black",
            )
    ax.set_title("① Fragment obrazu\n(jasność pikseli)", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Step 2: Gradient magnitude
    ax = axes[1]
    gx = np.array([[0, 150, 0], [0, 150, 0], [0, 150, 0]])
    ax.imshow(gx, cmap="gray", vmin=0, vmax=255)
    for i in range(3):
        for j in range(3):
            ax.text(
                j,
                i,
                str(gx[i, j]),
                ha="center",
                va="center",
                fontsize=FS_LABEL,
                fontweight="bold",
                color="white" if gx[i, j] > _GRADIENT_BRIGHT_THRESH else "black",
            )
    ax.set_title("② Gradient Gx\n(krawędź pionowa!)", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Step 3: Cell histogram
    ax = axes[2]
    angles = ["0°", "20°", "40°", "60°", "80°", "100°", "120°", "140°", "160°"]
    values = [150, 0, 0, 0, 0, 0, 0, 0, 0]
    bars = ax.bar(range(9), values, color=GRAY3, edgecolor=LN, linewidth=0.5)
    bars[0].set_facecolor(GRAY5)
    ax.set_xticks(range(9))
    ax.set_xticklabels(angles, fontsize=5, rotation=45)
    ax.set_title(
        "③ Histogram komórki\n(bin 0° = krawędź pionowa)",
        fontsize=FS,
        fontweight="bold",
    )
    ax.set_ylabel("siła", fontsize=FS_SMALL)

    # Step 4: Block normalization
    ax = axes[3]
    # 2x2 block of cells
    for i in range(2):
        for j in range(2):
            rect = mpatches.Rectangle(
                (j * 1.2, (1 - i) * 1.2),
                1.0,
                1.0,
                lw=1.2,
                edgecolor=LN,
                facecolor=GRAY4,
            )
            ax.add_patch(rect)
            ax.text(
                j * 1.2 + 0.5,
                (1 - i) * 1.2 + 0.5,
                f"hist\n{i * 2 + j + 1}",
                ha="center",
                va="center",
                fontsize=FS_SMALL,
            )
    ax.add_patch(
        mpatches.Rectangle(
            (-0.1, -0.1), 2.6, 2.6, lw=2, edgecolor=LN, facecolor="none", linestyle="--"
        )
    )
    ax.text(
        1.2,
        -0.4,
        "blok 2x2 → L2-norm",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    ax.set_xlim(-0.3, 2.8)
    ax.set_ylim(-0.7, 2.8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "④ Normalizacja bloków\n(odporność na oświetlenie)",
        fontsize=FS,
        fontweight="bold",
    )

    fig.tight_layout()
    save_fig(fig, "q24_hog_gradient_steps.png")


# ============================================================
# 3. Viola-Jones Cascade
# ============================================================
def draw_viola_jones_cascade() -> None:
    """Draw viola jones cascade."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-1.5, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Viola-Jones — kaskada klasyfikatorów (SITO)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    # Input
    draw_box(
        ax,
        -0.3,
        2.5,
        1.5,
        1.2,
        "500 000\nokien",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )

    stages = [
        ("Etap 1\n2 cechy", "50%\nodrzucone", "250 000", GRAY4),
        ("Etap 2\n10 cech", "80%\nodrzucone", "50 000", GRAY4),
        ("Etap 3\n25 cech", "90%\nodrzucone", "5 000", GRAY4),
        ("Etap 25\n200 cech", "99%\nodrzucone", "50", GRAY3),
    ]

    x_pos = 1.6
    for i, (label, reject, remain, col) in enumerate(stages):
        # Stage box
        draw_box(
            ax, x_pos, 2.5, 1.6, 1.2, label, fill=col, fontsize=FS, fontweight="bold"
        )

        # Arrow from previous
        draw_arrow(ax, x_pos - 0.3, 3.1, x_pos - 0.05, 3.1, lw=1.5)

        # Reject arrow down
        draw_arrow(ax, x_pos + 0.8, 2.45, x_pos + 0.8, 1.6, lw=1.2)
        ax.text(
            x_pos + 0.8,
            1.3,
            reject,
            ha="center",
            fontsize=FS_SMALL,
            color="black",
            style="italic",
        )
        ax.text(
            x_pos + 0.8,
            0.8,
            "✗ NIE-TWARZ",
            ha="center",
            fontsize=FS_SMALL,
            fontweight="bold",
        )

        # Remaining count above
        if i < len(stages) - 1:
            ax.text(
                x_pos + 2.0,
                3.9,
                f"→ {remain}",
                ha="center",
                fontsize=FS_SMALL,
                style="italic",
            )

        # Dots between stage 3 and stage 25
        if i == _DOTS_STAGE_IDX:
            ax.text(
                x_pos + 2.0, 3.1, "· · ·", ha="center", fontsize=12, fontweight="bold"
            )
            x_pos += 2.5
        else:
            x_pos += 2.1

    # Final output
    draw_arrow(ax, x_pos + 0.3, 3.1, x_pos + 0.9, 3.1, lw=1.5)
    draw_box(
        ax,
        x_pos + 0.5,
        2.5,
        1.3,
        1.2,
        "~50\nTWARZE\n✓",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Timing info
    ax.text(
        5.0,
        -0.5,
        "Czas: 99% okien odrzucone w etapach 1-3 (~5 μs każde)\n"
        "Tylko 0.01% dochodzi do etapu 25 → cały obraz w ~30 ms = 30+ fps",
        ha="center",
        fontsize=FS,
        style="italic",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    save_fig(fig, "q24_viola_jones_cascade.png")
