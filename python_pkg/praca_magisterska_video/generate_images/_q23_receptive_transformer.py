"""Receptive field and transformer diagram generators."""

from __future__ import annotations

from _q23_common import (
    _HIGHLIGHT_END,
    _HIGHLIGHT_START,
    ACCENT,
    ACCENT_LIGHT,
    BLACK,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY3,
    GRAY5,
    GREEN_ACCENT,
    RED_ACCENT,
    WHITE,
    _save_figure,
    plt,
)
from matplotlib import patches


def generate_receptive_field() -> None:
    """Generate receptive field."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 4))

    def draw_grid(
        ax: patches.Axes,
        size: int,
        highlight_cells: list[tuple[int, int]],
        highlight_color: str,
        title: str,
        grid_offset: tuple[int, int] = (0, 0),
    ) -> None:
        """Draw grid."""
        ox, oy = grid_offset
        for i in range(size):
            for j in range(size):
                color = WHITE
                if (i, j) in highlight_cells:
                    color = highlight_color
                rect = patches.Rectangle(
                    (ox + j, oy + size - 1 - i),
                    1,
                    1,
                    facecolor=color,
                    edgecolor=GRAY3,  # Use GRAY3 instead of GRAY4 since unused
                    linewidth=0.5,
                )
                ax.add_patch(rect)
        ax.set_title(title, fontsize=FS_TITLE, fontweight="bold")

    # --- Panel 1: Standard 3x3 conv receptive field ---
    ax = axes[0]
    ax.set_xlim(-0.5, 7.5)
    ax.set_ylim(-1, 8)
    ax.set_aspect("equal")
    ax.axis("off")

    # 7x7 input grid
    highlight_3x3 = [
        (2, 2),
        (2, 3),
        (2, 4),
        (3, 2),
        (3, 3),
        (3, 4),
        (4, 2),
        (4, 3),
        (4, 4),
    ]
    draw_grid(ax, 7, highlight_3x3, ACCENT_LIGHT, "Zwykła conv 3x3")
    ax.text(
        3.5,
        -0.5,
        "RF = 3x3 pikseli",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color=ACCENT,
    )

    # --- Panel 2: Dilated conv (rate=2) ---
    ax = axes[1]
    ax.set_xlim(-0.5, 7.5)
    ax.set_ylim(-1, 8)
    ax.set_aspect("equal")
    ax.axis("off")

    # 7x7 input grid with dilated highlights
    highlight_dilated = [
        (1, 1),
        (1, 3),
        (1, 5),
        (3, 1),
        (3, 3),
        (3, 5),
        (5, 1),
        (5, 3),
        (5, 5),
    ]
    draw_grid(ax, 7, highlight_dilated, "#FFCDD2", "Dilated conv 3x3\n(rate=2)")
    ax.text(
        3.5,
        -0.5,
        "RF = 5x5, ale 9 parametrów!",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color=RED_ACCENT,
    )

    # Connect dots to show pattern
    dots_x = [1.5, 3.5, 5.5, 1.5, 3.5, 5.5, 1.5, 3.5, 5.5]
    dots_y = [5.5, 5.5, 5.5, 3.5, 3.5, 3.5, 1.5, 1.5, 1.5]
    ax.scatter(dots_x, dots_y, c=RED_ACCENT, s=30, zorder=5)

    # --- Panel 3: Comparison ---
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "Receptive Field\n(pole widzenia neuronu)", fontsize=FS_TITLE, fontweight="bold"
    )

    y = 8.5
    lines = [
        ("RF = ile pikseli WEJŚCIOWYCH", FS, BLACK, "bold"),
        ("wpływa na JEDEN piksel wyjścia", FS, BLACK, "bold"),
        ("", 0, "", ""),
        ("Rate (współczynnik dylatacji):", FS, BLACK, "bold"),
        ('  rate=1: filtr „dotyka" sąsiadów', FS_SMALL, BLACK, "normal"),
        ("  rate=2: co drugi piksel → RF = 5x5", FS_SMALL, BLACK, "normal"),
        ("  rate=3: co trzeci → RF = 7x7", FS_SMALL, BLACK, "normal"),
        ("  WIĘCEJ kontekstu, TE SAME wagi!", FS_SMALL, GREEN_ACCENT, "bold"),
        ("", 0, "", ""),
        ("Dlaczego ważne w segmentacji?", FS, BLACK, "bold"),
        ("  Piksel sam nie wie czym jest.", FS_SMALL, BLACK, "normal"),
        ("  Potrzebuje KONTEKSTU (otoczenia).", FS_SMALL, BLACK, "normal"),
        ("  Większe RF → widzi obok budynki", FS_SMALL, BLACK, "normal"),
        ('  → wie, że TEN piksel to „droga"', FS_SMALL, GREEN_ACCENT, "bold"),
        ("", 0, "", ""),
        ("Global Average Pooling:", FS, BLACK, "bold"),
        ("  Mapa HxWxC → 1x1xC", FS_SMALL, BLACK, "normal"),
        ("  Średnia z CAŁEGO feature map", FS_SMALL, BLACK, "normal"),
        ("  RF = nieskończone (cały obraz)", FS_SMALL, GREEN_ACCENT, "bold"),
    ]
    for txt, size, color, weight in lines:
        if txt == "":
            y -= 0.2
            continue
        ax.text(0.5, y, txt, fontsize=size, color=color, fontweight=weight, va="top")
        y -= 0.45

    _save_figure("q23_receptive_field.png")


def generate_transformer() -> None:
    """Generate transformer."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 4))

    # --- Panel 1: CNN local vs Transformer global ---
    ax = axes[0]
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-1.5, 8.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("CNN: widzi LOKALNIE", fontsize=FS_TITLE, fontweight="bold")

    # Draw 8x8 grid
    for i in range(8):
        for j in range(8):
            color = WHITE
            if (
                _HIGHLIGHT_START <= i <= _HIGHLIGHT_END
                and _HIGHLIGHT_START <= j <= _HIGHLIGHT_END
            ):
                color = ACCENT_LIGHT
            rect = patches.Rectangle(
                (j, 7 - i), 1, 1, facecolor=color, edgecolor=GRAY3, linewidth=0.3
            )
            ax.add_patch(rect)

    # Highlight center
    rect = patches.Rectangle(
        (4, 4), 1, 1, facecolor=RED_ACCENT, edgecolor=BLACK, linewidth=1.5, alpha=0.7
    )
    ax.add_patch(rect)
    ax.text(
        4.5,
        4.5,
        "?",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
        color=WHITE,
    )
    ax.text(
        4.5,
        -0.8,
        "Filtr 3x3 widzi tylko\n9 sąsiednich pikseli",
        fontsize=FS_SMALL,
        ha="center",
        color=ACCENT,
    )

    # --- Panel 2: Transformer global ---
    ax = axes[1]
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-1.5, 8.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Transformer: widzi GLOBALNIE", fontsize=FS_TITLE, fontweight="bold")

    # Draw 8x8 grid all highlighted
    for i in range(8):
        for j in range(8):
            color = "#FFCDD2"
            rect = patches.Rectangle(
                (j, 7 - i), 1, 1, facecolor=color, edgecolor=GRAY3, linewidth=0.3
            )
            ax.add_patch(rect)

    rect = patches.Rectangle(
        (4, 4), 1, 1, facecolor=RED_ACCENT, edgecolor=BLACK, linewidth=1.5, alpha=0.9
    )
    ax.add_patch(rect)
    ax.text(
        4.5,
        4.5,
        "?",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
        color=WHITE,
    )
    ax.text(
        4.5,
        -0.8,
        'Self-attention „pyta"\nALL 64 piksele naraz',
        fontsize=FS_SMALL,
        ha="center",
        color=RED_ACCENT,
    )

    # --- Panel 3: SOTA + Transformer explanation ---
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Transformer & SOTA", fontsize=FS_TITLE, fontweight="bold")

    y = 9.2
    lines = [
        ("Transformer:", FS, BLACK, "bold"),
        ("  Architektura z 2017 (Vaswani et al.)", FS_SMALL, BLACK, "normal"),
        ("  Oryginalnie do NLP (tłumaczenie)", FS_SMALL, BLACK, "normal"),
        ("  Kluczowy mechanizm: SELF-ATTENTION", FS_SMALL, ACCENT, "bold"),
        ("", 0, "", ""),
        ("Self-attention w skrócie:", FS, BLACK, "bold"),
        ("  Każdy piksel tworzy trzy wektory:", FS_SMALL, BLACK, "normal"),
        ('    Q (Query — „czego szukam?")', FS_SMALL, ACCENT, "normal"),
        ('    K (Key — „co oferuję innych")', FS_SMALL, RED_ACCENT, "normal"),
        ('    V (Value — „moja wartość")', FS_SMALL, GREEN_ACCENT, "normal"),
        ("  Attention = softmax(Q·Kᵀ/√d)·V", FS_SMALL, BLACK, "bold"),
        ("  Koszt: O(n²) — n=liczba pikseli", FS_SMALL, RED_ACCENT, "normal"),
        ("", 0, "", ""),
        ("SOTA = State Of The Art:", FS, BLACK, "bold"),
        ("  Najlepszy znany wynik na benchmarku", FS_SMALL, BLACK, "normal"),
        ('  Np. „mIoU 85.1% na ADE20K = SOTA"', FS_SMALL, BLACK, "normal"),
        ("  Ciągle się zmienia (nowy paper", FS_SMALL, GRAY5, "normal"),
        ("  → nowy SOTA)", FS_SMALL, GRAY5, "normal"),
    ]
    for txt, size, color, weight in lines:
        if txt == "":
            y -= 0.15
            continue
        ax.text(0.3, y, txt, fontsize=size, color=color, fontweight=weight, va="top")
        y -= 0.45

    _save_figure("q23_transformer_attention.png")
