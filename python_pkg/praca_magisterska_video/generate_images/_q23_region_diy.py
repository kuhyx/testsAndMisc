"""Region growing and DIY thresholding diagram generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q23_common import (
    _BRIGHT_THRESHOLD,
    _OTSU_THRESHOLD,
    ACCENT,
    ACCENT_LIGHT,
    BLACK,
    FS,
    FS_SMALL,
    FS_TINY,
    FS_TITLE,
    GRAY3,
    GRAY4,
    GRAY5,
    GREEN_ACCENT,
    RED_ACCENT,
    WHITE,
    _save_figure,
    np,
    plt,
    rng,
)
from matplotlib import patches

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _draw_region_growing_grid(ax: Axes) -> None:
    """Draw panel 2: region growing step-by-step grid."""
    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-1.5, 7.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Region Growing: krok po kroku",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    pixel_grid = np.array(
        [
            [150, 153, 148, 200, 210, 205],
            [147, 155, 152, 195, 208, 200],
            [145, 148, 160, 190, 195, 210],
            [200, 195, 190, 155, 148, 150],
            [210, 205, 200, 150, 152, 145],
            [215, 208, 195, 148, 147, 155],
        ]
    )
    region_mask = np.array(
        [
            [1, 1, 1, 0, 0, 0],
            [1, 1, 1, 0, 0, 0],
            [1, 1, 1, 0, 0, 0],
            [0, 0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1, 1],
        ]
    )

    for i in range(6):
        for j in range(6):
            v = pixel_grid[i, j]
            if region_mask[i, j] == 1 and v < _BRIGHT_THRESHOLD:
                cell_color = ACCENT_LIGHT
            elif region_mask[i, j] == 1:
                cell_color = "#E0E0E0"
            else:
                cell_color = WHITE
            if i == 1 and j == 1:
                cell_color = "#FFD54F"
            rect = patches.Rectangle(
                (j, 5 - i),
                1,
                1,
                facecolor=cell_color,
                edgecolor=GRAY4,
                linewidth=0.5,
            )
            ax.add_patch(rect)
            ax.text(
                j + 0.5,
                5 - i + 0.5,
                str(v),
                ha="center",
                va="center",
                fontsize=FS_TINY,
                fontweight="bold",
            )

    ax.annotate(
        "SEED\n(155)",
        xy=(1.5, 4.5),
        fontsize=FS_SMALL,
        ha="center",
        color=RED_ACCENT,
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "color": RED_ACCENT},
        xytext=(-0.5, 7),
    )
    ax.text(
        3,
        -0.8,
        "Próg = 20\nNiebieski = region (|val - seed| < 20)",
        fontsize=FS_TINY,
        ha="center",
        color=ACCENT,
    )


def _draw_bfs_expansion(ax: Axes) -> None:
    """Draw panel 3: BFS expansion visualization."""
    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-1.5, 7.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Rosnący region (BFS)",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    wave_colors = ["#FFD54F", "#FFF176", "#FFF9C4", ACCENT_LIGHT, "#B3D4FC"]
    wave_labels = ["Seed", "Fala 1", "Fala 2", "Fala 3", "Fala 4"]
    waves = [
        [(1, 1)],
        [(0, 1), (1, 0), (1, 2), (2, 1)],
        [(0, 0), (0, 2), (2, 0), (2, 2)],
    ]

    for i in range(6):
        for j in range(6):
            cell_color = WHITE
            for w_idx, wave in enumerate(waves):
                if (i, j) in wave:
                    cell_color = wave_colors[w_idx]
            rect = patches.Rectangle(
                (j, 5 - i),
                1,
                1,
                facecolor=cell_color,
                edgecolor=GRAY4,
                linewidth=0.5,
            )
            ax.add_patch(rect)

    seed_x, seed_y = 1.5, 4.5
    for dx, dy, _label in [
        (0, 1, ""),
        (0, -1, ""),
        (1, 0, ""),
        (-1, 0, ""),
    ]:
        ax.annotate(
            "",
            xy=(seed_x + dx * 0.7, seed_y + dy * 0.7),
            xytext=(seed_x, seed_y),
            arrowprops={
                "arrowstyle": "->",
                "color": RED_ACCENT,
                "lw": 1.2,
            },
        )

    ax.text(
        3,
        -0.5,
        "BFS: sprawdzaj sąsiadów,\ndodawaj podobne do kolejki",
        fontsize=FS_TINY,
        ha="center",
        color=GRAY5,
    )

    for w_idx, (wave_color, label) in enumerate(
        zip(wave_colors[:3], wave_labels[:3], strict=False)
    ):
        rect = patches.Rectangle(
            (4, 6.5 - w_idx * 0.7),
            0.5,
            0.5,
            facecolor=wave_color,
            edgecolor=GRAY4,
            linewidth=0.5,
        )
        ax.add_patch(rect)
        ax.text(
            4.8,
            6.75 - w_idx * 0.7,
            label,
            fontsize=FS_TINY,
            va="center",
        )


def generate_region_growing() -> None:
    """Generate region growing."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 4.2))

    # --- Panel 1: Manual vs automatic seed ---
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Seed: ręcznie vs automatycznie", fontsize=FS_TITLE, fontweight="bold")

    y = 9.2
    lines = [
        ("Ręczny seed:", FS, ACCENT, "bold"),
        ("  Użytkownik klika na obraz", FS_SMALL, BLACK, "normal"),
        ('  → „tu jest obiekt, od tego zacznij"', FS_SMALL, BLACK, "normal"),
        ("  Użycie: segmentacja interaktywna", FS_SMALL, GRAY5, "normal"),
        ("  (np. Photoshop — magic wand tool)", FS_SMALL, GRAY5, "normal"),
        ("", 0, "", ""),
        ("Automatyczny seed:", FS, RED_ACCENT, "bold"),
        ("  1. Histogram → lokalne maxima", FS_SMALL, BLACK, "normal"),
        ("     (najczęstsza jasność → seed)", FS_SMALL, GRAY5, "normal"),
        ("  2. Grid: siatka co N pikseli", FS_SMALL, BLACK, "normal"),
        ("     (np. seed co 50 px → 100 seedów)", FS_SMALL, GRAY5, "normal"),
        ("  3. Losowe próbkowanie", FS_SMALL, BLACK, "normal"),
        ("  4. Ekstrema lokalne gradientu", FS_SMALL, BLACK, "normal"),
        ("", 0, "", ""),
        ("Dlaczego OR?", FS, GREEN_ACCENT, "bold"),
        ("  Ręczny → precyzyjny, ale wolny", FS_SMALL, BLACK, "normal"),
        ("  Auto → szybki, ale over-segmentation", FS_SMALL, BLACK, "normal"),
    ]
    for txt, size, color, weight in lines:
        if txt == "":
            y -= 0.15
            continue
        ax.text(0.3, y, txt, fontsize=size, color=color, fontweight=weight, va="top")
        y -= 0.45

    # --- Panel 2: Region growing step by step ---
    _draw_region_growing_grid(axes[1])

    # --- Panel 3: BFS expansion ---
    _draw_bfs_expansion(axes[2])

    _save_figure("q23_region_growing.png")


def _draw_otsu_variance_and_pseudocode(
    ax_var: Axes,
    ax_code: Axes,
    img: np.ndarray,
) -> int:
    """Draw panels 4 and 5: Otsu variance plot and pseudocode."""
    thresholds = range(10, 245)
    variances = []
    for t in thresholds:
        c0 = img[img <= t].ravel()
        c1 = img[img > t].ravel()
        if len(c0) == 0 or len(c1) == 0:
            variances.append(np.nan)
            continue
        w0 = len(c0) / len(img.ravel())
        w1 = len(c1) / len(img.ravel())
        var = w0 * np.var(c0) + w1 * np.var(c1)
        variances.append(var)

    ax_var.plot(list(thresholds), variances, color=ACCENT, linewidth=1.5)
    best_t = list(thresholds)[np.nanargmin(variances)]
    ax_var.axvline(
        x=best_t,
        color=RED_ACCENT,
        linewidth=1.5,
        linestyle="--",
        label=f"Otsu T={best_t}",
    )
    ax_var.scatter(
        [best_t],
        [np.nanmin(variances)],
        c=RED_ACCENT,
        s=60,
        zorder=5,
    )
    ax_var.set_xlabel("Próg T", fontsize=FS_SMALL)
    ax_var.set_ylabel("σ² wewnątrzklasowa", fontsize=FS_SMALL)
    ax_var.set_title(
        "Krok 4: Otsu szuka min σ²",
        fontsize=FS,
        fontweight="bold",
    )
    ax_var.legend(fontsize=FS_TINY)

    ax_code.set_xlim(0, 10)
    ax_code.set_ylim(0, 10)
    ax_code.axis("off")
    ax_code.set_title("Pseudokod Otsu", fontsize=FS, fontweight="bold")

    code_lines = [
        "best_T = 0",
        "min_var = ∞",
        "",
        "for T in 0..255:",
        "  c0 = piksele z jasność ≤ T",
        "  c1 = piksele z jasność > T",
        "  w0 = len(c0) / len(all)",
        "  w1 = len(c1) / len(all)",
        "  var = w0·var(c0) + w1·var(c1)",
        "  if var < min_var:",
        "     min_var = var",
        "     best_T = T",
        "",
        "return best_T  # optymalny próg",
    ]
    for i, line in enumerate(code_lines):
        txt_color = ACCENT if "best_T = T" in line or "return" in line else BLACK
        ax_code.text(
            0.5,
            9.5 - i * 0.65,
            line,
            fontsize=FS_TINY,
            fontfamily="monospace",
            color=txt_color,
            fontweight="bold" if txt_color == ACCENT else "normal",
        )
    return int(best_t)


def generate_diy_thresholding() -> None:
    """Generate diy thresholding."""
    _fig, axes = plt.subplots(2, 3, figsize=(11, 7))

    # Create a simple synthetic image: dark circle on bright background
    size = 64
    img = np.ones((size, size)) * 200  # bright background
    yy, xx = np.mgrid[:size, :size]
    mask = ((xx - 32) ** 2 + (yy - 32) ** 2) < 15**2
    img[mask] = 60  # dark circle
    # Add some noise
    img += rng.normal(0, 10, img.shape)
    img = np.clip(img, 0, 255)

    # --- Panel 1: Original image ---
    ax = axes[0, 0]
    ax.imshow(img, cmap="gray", vmin=0, vmax=255)
    ax.set_title("Krok 1: obraz wejściowy", fontsize=FS, fontweight="bold")
    ax.axis("off")
    ax.text(32, -3, "64x64 pikseli, szare", fontsize=FS_TINY, ha="center")

    # --- Panel 2: Histogram ---
    ax = axes[0, 1]
    counts, _bins, _ = ax.hist(
        img.ravel(), bins=50, color=GRAY3, edgecolor=GRAY5, linewidth=0.5
    )
    ax.axvline(
        x=128, color=RED_ACCENT, linewidth=2, linestyle="--", label="T=128 (Otsu)"
    )
    ax.set_xlabel("Jasność", fontsize=FS_SMALL)
    ax.set_ylabel("Piksele", fontsize=FS_SMALL)
    ax.set_title("Krok 2: histogram\n(bimodalny!)", fontsize=FS, fontweight="bold")
    ax.legend(fontsize=FS_TINY)
    ax.annotate(
        "Garb 1\n(obiekt)",
        xy=(60, max(counts) * 0.5),
        fontsize=FS_TINY,
        ha="center",
        color=ACCENT,
        fontweight="bold",
    )
    ax.annotate(
        "Garb 2\n(tło)",
        xy=(200, max(counts) * 0.5),
        fontsize=FS_TINY,
        ha="center",
        color=RED_ACCENT,
        fontweight="bold",
    )

    # --- Panel 3: Thresholding result ---
    ax = axes[0, 2]
    binary = (img > _OTSU_THRESHOLD).astype(float)
    ax.imshow(binary, cmap="gray", vmin=0, vmax=1)
    ax.set_title("Krok 3: progowanie T=128", fontsize=FS, fontweight="bold")
    ax.axis("off")
    ax.text(32, -3, "Biały = tło, Czarny = obiekt", fontsize=FS_TINY, ha="center")

    # --- Panels 4+5: Otsu variance plot + pseudocode ---
    best_t = _draw_otsu_variance_and_pseudocode(
        axes[1, 0],
        axes[1, 1],
        img,
    )

    # --- Panel 6: Final result with Otsu ---
    ax = axes[1, 2]
    binary_otsu = (img > best_t).astype(float)
    ax.imshow(binary_otsu, cmap="gray", vmin=0, vmax=1)
    ax.set_title(f"Krok 5: wynik Otsu (T={best_t})", fontsize=FS, fontweight="bold")
    ax.axis("off")
    ax.text(
        32,
        -3,
        "Automatyczny próg!",
        fontsize=FS_TINY,
        ha="center",
        color=GREEN_ACCENT,
        fontweight="bold",
    )

    _save_figure("q23_diy_thresholding.png")
