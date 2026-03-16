"""Two-stage vs one-stage table, ROI pooling, DETR, and sliding window."""

from __future__ import annotations

from _q24_common import (
    _DATA_BRIGHT_THRESH,
    FS,
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
    draw_table,
    np,
    plt,
    rng,
    save_fig,
)
import matplotlib.patches as mpatches


# ============================================================
# 12. Two-stage vs One-stage comparison table
# ============================================================
def draw_two_vs_one_stage() -> None:
    """Draw two vs one stage."""
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Two-stage vs One-stage — porównanie",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=8,
    )

    headers = ["Cecha", "Two-stage\n(Faster R-CNN)", "One-stage\n(YOLO)"]
    rows = [
        ["Szybkość", "~5 fps", "45-155 fps"],
        ["Dokładność (mAP)", "wyższa (historycznie)", "dorównuje (YOLOv8)"],
        ["Małe obiekty", "lepszy", "gorszy (SSD/FPN pomaga)"],
        ["Architektura", "2 etapy + NMS", "1 etap + NMS"],
        ["Real-time?", "NIE", "TAK"],
    ]
    col_widths = [2.5, 3.5, 3.5]
    draw_table(
        ax,
        headers,
        rows,
        0.2,
        3.8,
        col_widths,
        row_h=0.65,
        fontsize=FS,
        header_fontsize=FS,
    )

    save_fig(fig, "q24_two_vs_one_stage.png")


# ============================================================
# 13. ROI Pooling illustration
# ============================================================
def draw_roi_pooling() -> None:
    """Draw roi pooling."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle(
        "ROI Pooling — dowolny rozmiar → stały rozmiar",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Feature map with ROI
    ax = axes[0]
    # Draw feature map grid
    fm = rng.integers(0, 10, (8, 8))
    ax.imshow(fm, cmap="gray", vmin=0, vmax=10, alpha=0.3)
    for i in range(9):
        ax.axhline(y=i - 0.5, color=LN, lw=0.3)
        ax.axvline(x=i - 0.5, color=LN, lw=0.3)
    # ROI rectangle
    ax.add_patch(
        mpatches.Rectangle(
            (1.5, 1.5), 4, 4, facecolor="none", edgecolor=LN, lw=3, linestyle="-"
        )
    )
    ax.text(3.5, 0.8, "ROI", ha="center", fontsize=FS, fontweight="bold")
    ax.set_xlim(-0.5, 7.5)
    ax.set_ylim(7.5, -0.5)
    ax.set_title("① Feature map\nz zaznaczonym ROI", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # ROI divided into grid
    ax = axes[1]
    roi_data = np.array(
        [
            [1, 3, 2, 1],
            [0, 5, 1, 6],
            [0, 4, 1, 0],
            [7, 2, 9, 1],
        ]
    )
    ax.imshow(roi_data, cmap="gray", vmin=0, vmax=10)
    for i in range(5):
        ax.axhline(y=i - 0.5, color=LN, lw=1)
        ax.axvline(x=i - 0.5, color=LN, lw=1)
    # Grid lines for 2x2 pooling
    ax.axhline(y=0.5, color=LN, lw=3, linestyle="--")
    ax.axvline(x=0.5, color=LN, lw=3, linestyle="--")
    for i in range(4):
        for j in range(4):
            ax.text(
                j,
                i,
                str(roi_data[i, j]),
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color="white" if roi_data[i, j] > _DATA_BRIGHT_THRESH else "black",
            )
    ax.set_title("② ROI podzielony\nna siatkę 2x2", fontsize=FS, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    # Output after pooling
    ax = axes[2]
    out = np.array([[5, 6], [7, 9]])
    ax.imshow(out, cmap="gray", vmin=0, vmax=10)
    for i in range(3):
        ax.axhline(y=i - 0.5, color=LN, lw=1.5)
        ax.axvline(x=i - 0.5, color=LN, lw=1.5)
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                str(out[i, j]),
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color="white" if out[i, j] > _DATA_BRIGHT_THRESH else "black",
            )
    ax.set_title(
        "③ Po ROI Pool 2x2\n(max z każdej komórki)", fontsize=FS, fontweight="bold"
    )
    ax.set_xticks([])
    ax.set_yticks([])

    fig.tight_layout()
    save_fig(fig, "q24_roi_pooling.png")


# ============================================================
# 14. DETR Pipeline
# ============================================================
def draw_detr_pipeline() -> None:
    """Draw detr pipeline."""
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(-1, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "DETR — Transformer do detekcji (bez NMS, bez anchorów)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    # Pipeline
    draw_box(ax, 0, 1.5, 1.5, 1.5, "Obraz\nwejściowy", fill=GRAY1, fontsize=FS)
    draw_arrow(ax, 1.6, 2.25, 2.1, 2.25, lw=1.5)

    draw_box(
        ax,
        2.2,
        1.5,
        1.5,
        1.5,
        "CNN\nBackbone\n(ResNet)",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 3.8, 2.25, 4.3, 2.25, lw=1.5)

    draw_box(
        ax,
        4.4,
        1.5,
        1.8,
        1.5,
        "Transformer\nEncoder\n(self-attention)",
        fill=GRAY2,
        fontsize=FS,
    )
    draw_arrow(ax, 6.3, 2.25, 6.8, 2.25, lw=1.5)

    draw_box(
        ax,
        6.9,
        1.5,
        1.8,
        1.5,
        "Transformer\nDecoder\n(N=100 queries)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Output branches
    draw_arrow(ax, 8.8, 2.5, 9.5, 3.0, lw=1.2)
    draw_box(ax, 9.6, 2.7, 1.5, 0.7, "klasa₁...klasa₁₀₀", fill=GRAY4, fontsize=FS_SMALL)

    draw_arrow(ax, 8.8, 2.0, 9.5, 1.5, lw=1.2)
    draw_box(ax, 9.6, 1.2, 1.5, 0.7, "bbox₁...bbox₁₀₀", fill=GRAY4, fontsize=FS_SMALL)

    # Annotations
    ax.text(
        7.8,
        0.5,
        '100 object queries → 5 obiektów + 95x "brak"',
        ha="center",
        fontsize=FS,
        style="italic",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.text(
        5.5,
        0.0,
        "Hungarian matching (trening): optymalne dopasowanie predykcji do GT",
        ha="center",
        fontsize=FS_SMALL,
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    # Big benefit box
    ax.text(
        5.5,
        4.0,
        "BEZ anchorów • BEZ NMS • end-to-end • prosty pipeline",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY2, "edgecolor": GRAY3},
    )

    save_fig(fig, "q24_detr_pipeline.png")


# ============================================================
# 15. Sliding Window illustration
# ============================================================
def draw_sliding_window() -> None:
    """Draw sliding window."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle(
        "Sliding Window — najprostsze podejście do detekcji",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    # Multi-position
    ax = axes[0]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 8, 6, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    # Grid of sliding windows
    for i in range(4):
        for j in range(3):
            ax.add_patch(
                mpatches.Rectangle(
                    (i * 1.8 + 0.2, j * 1.8 + 0.2),
                    1.5,
                    1.5,
                    facecolor="none",
                    edgecolor=LN,
                    lw=0.6,
                    linestyle="--",
                )
            )
    # Highlight current window
    ax.add_patch(
        mpatches.Rectangle((2.0, 2.0), 1.5, 1.5, facecolor="none", edgecolor=LN, lw=2.5)
    )
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-0.5, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("① Wiele pozycji\n(krok co 8 px)", fontsize=FS, fontweight="bold")

    # Multi-scale
    ax = axes[1]
    ax.add_patch(
        mpatches.Rectangle((0, 0), 6, 5, facecolor=GRAY4, edgecolor=LN, lw=1.5)
    )
    sizes = [(0.8, 0.8), (1.5, 1.5), (2.5, 2.5), (3.5, 3.5)]
    for i, (w, h) in enumerate(sizes):
        ax.add_patch(
            mpatches.Rectangle(
                (0.3 + i * 0.3, 0.3 + i * 0.3),
                w,
                h,
                facecolor="none",
                edgecolor=LN,
                lw=1 + i * 0.3,
                linestyle=[":", "--", "-.", "-"][i],
            )
        )
    ax.text(3, 0, "4+ skal", ha="center", fontsize=FS_SMALL, fontweight="bold")
    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "② Wiele skal\n(obiekty mają różne rozmiary)", fontsize=FS, fontweight="bold"
    )

    # Count
    ax = axes[2]
    ax.axis("off")
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 5)

    lines = [
        ("Obraz: 640 x 480 px", 4.5),
        ("Okno: 64 x 64 px, krok 8 px", 3.8),
        ("Pozycje: ~72 x 52 = 3 744", 3.1),
        ("x 5 skal = 18 720 okien", 2.4),
        ("x klasyfikacja = WOLNE!", 1.7),
        ("→ ~3h na jeden obraz", 0.8),
    ]
    for text, yp in lines:
        fw = "bold" if "~3h" in text or "WOLNE" in text else "normal"
        col = GRAY2 if "WOLNE" in text or "~3h" in text else GRAY4
        ax.text(
            3.0,
            yp,
            text,
            ha="center",
            fontsize=FS,
            fontweight=fw,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": col, "edgecolor": GRAY3},
        )

    ax.set_title(
        "③ Dlaczego wolne?\n(miliony klasyfikacji)", fontsize=FS, fontweight="bold"
    )

    fig.tight_layout()
    save_fig(fig, "q24_sliding_window.png")
