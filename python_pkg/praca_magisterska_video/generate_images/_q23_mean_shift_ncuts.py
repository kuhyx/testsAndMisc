"""Mean shift and normalized cuts diagram generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q23_common import (
    _DARK_PIXEL_THRESHOLD,
    _GRID_LAST_IDX,
    ACCENT,
    ACCENT_LIGHT,
    BLACK,
    FS,
    FS_SMALL,
    FS_TINY,
    FS_TITLE,
    GRAY1,
    GRAY3,
    GRAY4,
    GRAY5,
    GRAY6,
    GREEN_ACCENT,
    RED_ACCENT,
    _render_text_lines,
    _save_figure,
    np,
    plt,
    rng,
)
from matplotlib import patches

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def generate_mean_shift() -> None:
    """Generate mean shift."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 4))

    # --- Panel 1: Feature space concept ---
    ax = axes[0]
    # Three clusters in 2D feature space (brightness, x-position)
    c1x = rng.normal(2, 0.5, 40)
    c1y = rng.normal(2, 0.5, 40)
    c2x = rng.normal(6, 0.6, 35)
    c2y = rng.normal(7, 0.5, 35)
    c3x = rng.normal(8, 0.4, 25)
    c3y = rng.normal(3, 0.6, 25)

    ax.scatter(c1x, c1y, c=GRAY4, s=15, alpha=0.7, zorder=3)
    ax.scatter(c2x, c2y, c=GRAY4, s=15, alpha=0.7, zorder=3)
    ax.scatter(c3x, c3y, c=GRAY4, s=15, alpha=0.7, zorder=3)

    # Label peaks
    ax.scatter([2], [2], c=RED_ACCENT, s=80, marker="*", zorder=5, label="Max gęstości")
    ax.scatter([6], [7], c=RED_ACCENT, s=80, marker="*", zorder=5)
    ax.scatter([8], [3], c=RED_ACCENT, s=80, marker="*", zorder=5)

    ax.set_xlabel("Cecha 1: jasność", fontsize=FS)
    ax.set_ylabel("Cecha 2: pozycja x", fontsize=FS)
    ax.set_title("Przestrzeń cech", fontsize=FS_TITLE, fontweight="bold")
    for lx, ly, ltxt in [
        (2, 0.3, "Klaster 1\n(ciemne, lewo)"),
        (6, 5.3, "Klaster 2\n(jasne, prawo)"),
        (8, 1.3, "Klaster 3\n(jasne, dół)"),
    ]:
        ax.text(lx, ly, ltxt, ha="center", fontsize=FS_TINY, color=GRAY6)
    ax.legend(fontsize=FS_SMALL, loc="upper left")

    # --- Panel 2: Kernel/window moving ---
    ax = axes[1]
    ax.scatter(c1x, c1y, c=ACCENT_LIGHT, s=15, alpha=0.7, zorder=3)
    ax.scatter(c2x, c2y, c=GRAY3, s=15, alpha=0.7, zorder=3)
    ax.scatter(c3x, c3y, c=GRAY3, s=15, alpha=0.7, zorder=3)

    # Show kernel movement
    path_x = [4.5, 3.8, 3.0, 2.3, 2.05]
    path_y = [4.0, 3.3, 2.7, 2.2, 2.03]

    for i, (px, py) in enumerate(zip(path_x, path_y, strict=False)):
        alpha = 0.3 + 0.15 * i
        circle = plt.Circle(
            (px, py),
            1.2,
            fill=False,
            edgecolor=ACCENT,
            linewidth=1.5,
            linestyle="--" if i < len(path_x) - 1 else "-",
            alpha=alpha,
        )
        ax.add_patch(circle)
        if i < len(path_x) - 1:
            ax.annotate(
                "",
                xy=(path_x[i + 1], path_y[i + 1]),
                xytext=(px, py),
                arrowprops={"arrowstyle": "->", "color": RED_ACCENT, "lw": 1.5},
            )

    ax.scatter([path_x[0]], [path_y[0]], c=ACCENT, s=50, marker="o", zorder=5)
    ax.scatter([path_x[-1]], [path_y[-1]], c=RED_ACCENT, s=80, marker="*", zorder=5)

    ax.text(
        4.5, 5.2, "Start: losowy\npiksel", fontsize=FS_SMALL, ha="center", color=ACCENT
    )
    ax.text(
        2.05,
        0.5,
        "Koniec: max\ngęstości",
        fontsize=FS_SMALL,
        ha="center",
        color=RED_ACCENT,
        fontweight="bold",
    )
    ax.text(
        7,
        8,
        "Okno (jądro)\nprzesuwa się\ndo skupiska",
        fontsize=FS_SMALL,
        ha="center",
        color=GRAY6,
        bbox={"boxstyle": "round", "facecolor": GRAY1, "edgecolor": GRAY3},
    )

    ax.set_xlabel("Cecha 1", fontsize=FS)
    ax.set_ylabel("Cecha 2", fontsize=FS)
    ax.set_title("Jądro → max gęstości", fontsize=FS_TITLE, fontweight="bold")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)

    # --- Panel 3: Why no K parameter ---
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Dlaczego bez K?", fontsize=FS_TITLE, fontweight="bold")

    lines = [
        ("K-means wymaga:", FS, RED_ACCENT, "bold"),
        ('  „Podaj K=3 klastry"', FS_SMALL, "black", "normal"),
        ("  Problem: skąd wiesz ile klastrów?", FS_SMALL, GRAY5, "normal"),
        ("", 0, "", ""),
        ("Mean Shift NIE wymaga K:", FS, GREEN_ACCENT, "bold"),
        ("  Każdy piksel startuje → toczy się", FS_SMALL, "black", "normal"),
        ("  → trafia do najbliższego szczytu", FS_SMALL, "black", "normal"),
        ("  → ile szczytów = tyle segmentów", FS_SMALL, "black", "normal"),
        ("  → automatycznie!", FS_SMALL, GREEN_ACCENT, "bold"),
        ("", 0, "", ""),
        ("Parametr: bandwidth (szerokość okna)", FS, "black", "bold"),
        ("  Duże okno → mało segmentów", FS_SMALL, "black", "normal"),
        ("  Małe okno → dużo segmentów", FS_SMALL, "black", "normal"),
        ("", 0, "", ""),
        ("Okno = jądro (kernel):", FS, "black", "bold"),
        ("  Koło o promieniu h wokół punktu.", FS_SMALL, "black", "normal"),
        ("  Oblicz średnią pikseli W oknie.", FS_SMALL, "black", "normal"),
        ("  Przesuń okno na tę średnią.", FS_SMALL, "black", "normal"),
        ("  Powtórz aż się zatrzyma.", FS_SMALL, "black", "normal"),
    ]
    _render_text_lines(ax, lines, start_y=9.0)

    _save_figure("q23_mean_shift.png")


def _draw_ncuts_pixel_grid(
    ax: Axes,
    pixel_vals: np.ndarray,
) -> None:
    """Draw 4x4 pixel grid with value labels and edge weights."""
    for i in range(4):
        for j in range(4):
            v = pixel_vals[i, j]
            gray_val = v / 255.0
            str(gray_val)
            rect = patches.Rectangle(
                (j - 0.4, 3 - i - 0.4),
                0.8,
                0.8,
                facecolor=(gray_val, gray_val, gray_val),
                edgecolor=BLACK,
                linewidth=0.8,
            )
            ax.add_patch(rect)
            text_color = "white" if v < _DARK_PIXEL_THRESHOLD else "black"
            ax.text(
                j,
                3 - i,
                str(v),
                ha="center",
                va="center",
                fontsize=FS_SMALL,
                color=text_color,
                fontweight="bold",
            )


def _draw_ncuts_edges(
    ax: Axes,
    pixel_vals: np.ndarray,
) -> None:
    """Draw weighted edges between adjacent pixels."""
    for i in range(4):
        for j in range(4):
            if j < _GRID_LAST_IDX:
                similarity = max(
                    0,
                    1 - abs(pixel_vals[i, j] - pixel_vals[i, j + 1]) / 255,
                )
                lw = similarity * 2.5 + 0.3
                alpha = similarity * 0.8 + 0.2
                ax.plot(
                    [j + 0.4, j + 0.6],
                    [3 - i, 3 - i],
                    color=GRAY5,
                    linewidth=lw,
                    alpha=alpha,
                )
            if i < _GRID_LAST_IDX:
                similarity = max(
                    0,
                    1 - abs(pixel_vals[i, j] - pixel_vals[i + 1, j]) / 255,
                )
                lw = similarity * 2.5 + 0.3
                alpha = similarity * 0.8 + 0.2
                ax.plot(
                    [j, j],
                    [3 - i - 0.4, 3 - i - 0.6],
                    color=GRAY5,
                    linewidth=lw,
                    alpha=alpha,
                )


def generate_normalized_cuts() -> None:
    """Generate normalized cuts."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 4))

    # --- Panel 1: Image as graph ---
    ax = axes[0]
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(-0.5, 4.5)
    ax.set_aspect("equal")
    ax.set_title("Obraz → graf", fontsize=FS_TITLE, fontweight="bold")

    pixel_vals = np.array(
        [
            [30, 35, 180, 190],
            [40, 30, 185, 200],
            [170, 180, 40, 35],
            [190, 175, 30, 45],
        ]
    )
    _draw_ncuts_pixel_grid(ax, pixel_vals)
    _draw_ncuts_edges(ax, pixel_vals)

    ax.text(
        2,
        -0.8,
        "Grube linie = duże podobieństwo\n(silna krawędź grafu)",
        ha="center",
        fontsize=FS_TINY,
        color=GRAY5,
    )
    ax.axis("off")

    # --- Panel 2: Cut concept ---
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Cięcie grafu (graph cut)", fontsize=FS_TITLE, fontweight="bold")

    # Draw two groups of nodes
    # Group A (dark pixels)
    positions_a = [(2, 7), (3, 8), (2, 5), (3, 6)]
    positions_b = [(7, 7), (8, 8), (7, 5), (8, 6)]

    # Intra-group edges (thick = similar)
    for i, (x1, y1) in enumerate(positions_a):
        for x2, y2 in positions_a[i + 1 :]:
            ax.plot([x1, x2], [y1, y2], color=ACCENT, linewidth=2, alpha=0.5)
    for i, (x1, y1) in enumerate(positions_b):
        for x2, y2 in positions_b[i + 1 :]:
            ax.plot([x1, x2], [y1, y2], color=RED_ACCENT, linewidth=2, alpha=0.5)

    # Inter-group edges (thin = dissimilar) — these get cut
    cut_edges = [((3, 8), (7, 7)), ((3, 6), (7, 5)), ((2, 5), (7, 5))]
    for (x1, y1), (x2, y2) in cut_edges:
        ax.plot([x1, x2], [y1, y2], color=GRAY4, linewidth=0.8, linestyle="--")

    # Draw nodes
    for x, y in positions_a:
        ax.scatter(x, y, c=ACCENT, s=120, zorder=5, edgecolors=BLACK, linewidth=0.8)
    for x, y in positions_b:
        ax.scatter(x, y, c="#FFCDD2", s=120, zorder=5, edgecolors=BLACK, linewidth=0.8)

    # Cut line
    ax.plot(
        [5, 5], [3.5, 9.5], color=RED_ACCENT, linewidth=2.5, linestyle="-", zorder=4
    )
    ax.text(
        5, 9.8, "CIĘCIE", ha="center", fontsize=FS, fontweight="bold", color=RED_ACCENT
    )

    ax.text(
        2.5,
        3.8,
        "Segment A\n(ciemne piksele)",
        ha="center",
        fontsize=FS_SMALL,
        color=ACCENT,
    )
    ax.text(
        7.5,
        3.8,
        "Segment B\n(jasne piksele)",
        ha="center",
        fontsize=FS_SMALL,
        color=RED_ACCENT,
    )

    # Formula
    ax.text(
        5,
        1.8,
        "Ncut(A,B) = cut(A,B)/assoc(A,V)\n                + cut(A,B)/assoc(B,V)",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
        bbox={"boxstyle": "round", "facecolor": GRAY1, "edgecolor": GRAY3},
    )
    ax.text(
        5,
        0.5,
        "Minimalizuj Ncut → tnij SŁABE krawędzie\nzachowuj SILNE (wewnątrz grupy)",
        ha="center",
        fontsize=FS_TINY,
        color=GRAY5,
    )

    # --- Panel 3: Algorithm summary ---
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Algorytm Normalized Cuts", fontsize=FS_TITLE, fontweight="bold")

    steps = [
        (
            "1. Zbuduj graf",
            "Piksele = węzły\nKrawędzie = podobieństwo"
            " sąsiadów\n(kolor, jasność, odległość)",
        ),
        (
            "2. Macierz podobieństwa W",
            "W[i,j] = exp(-|kolori - kolorj|² / σ²)"
            "\n→ im podobniejsze, tym wyższa waga",
        ),
        ("3. Macierz stopni D", "D[i,i] = Σ W[i,j]\n(suma wszystkich wag z węzła i)"),
        ("4. Rozwiąż problem własny", "(D-W)·y = λ·D·y\n→ drugi najm. wektor własny y"),
        ("5. Podziel wg y", "y[i] > 0 → segment A\ny[i] ≤ 0 → segment B"),
    ]

    y = 9.5
    for title, desc in steps:
        ax.text(0.5, y, title, fontsize=FS, fontweight="bold", va="top")
        y -= 0.4
        ax.text(0.8, y, desc, fontsize=FS_TINY, va="top", color=GRAY6)
        y -= 1.2

    ax.text(
        5,
        0.3,
        "Złożoność: O(n³) — wymaga eigen decomposition!",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
        color=RED_ACCENT,
    )

    _save_figure("q23_normalized_cuts.png")
