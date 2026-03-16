"""Otsu thresholding and watershed diagram generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q23_common import (
    _RIDGE_X,
    _VALLEY2_END,
    ACCENT,
    ACCENT_LIGHT,
    BLACK,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    GREEN_ACCENT,
    RED_ACCENT,
    _render_text_lines,
    _save_figure,
    np,
    plt,
    rng,
)
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _draw_otsu_variance_panel(ax: Axes) -> None:
    """Draw panel 2: within-class variance explanation."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Wariancja wewnątrzklasowa", fontsize=FS_TITLE, fontweight="bold")

    texts = [
        (
            "Wariancja = jak bardzo wartości\nróżnią się od średniej",
            FS,
            "black",
            "normal",
        ),
        ("", 0, "black", "normal"),
        ("Klasa 0 (piksele ≤ T):", FS, ACCENT, "bold"),
        ("  wartości: 30, 50, 45, 60, 55", FS_SMALL, "black", "normal"),
        ("  średnia μ₀ = 48", FS_SMALL, "black", "normal"),
        ("  σ₀² = ((30-48)²+(50-48)²+...)/5 = 108", FS_SMALL, "black", "normal"),
        ("", 0, "black", "normal"),
        ("Klasa 1 (piksele > T):", FS, RED_ACCENT, "bold"),
        ("  wartości: 180, 200, 190, 210, 195", FS_SMALL, "black", "normal"),
        ("  średnia μ₁ = 195", FS_SMALL, "black", "normal"),
        ("  σ₁² = ((180-195)²+...)/5 = 100", FS_SMALL, "black", "normal"),
        ("", 0, "black", "normal"),
        ("σ²_wewnątrz = w₀·σ₀² + w₁·σ₁²", FS, BLACK, "bold"),
        ("= 0.6·108 + 0.4·100 = 104.8", FS_SMALL, "black", "normal"),
        ("", 0, "black", "normal"),
        ("Otsu próbuje KAŻDE T: 0,1,...,255", FS_SMALL, GREEN_ACCENT, "bold"),
        ("Wybiera T dające MINIMUM σ²_wewnątrz", FS_SMALL, GREEN_ACCENT, "bold"),
    ]
    _render_text_lines(
        ax,
        texts,
        x_pos=0.3,
        start_y=9.2,
        y_step=0.55,
        y_empty_step=0.25,
    )


def generate_otsu_bimodal() -> None:
    """Generate otsu bimodal."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))

    # --- Panel 1: Bimodal histogram ---
    ax = axes[0]
    dark = rng.normal(60, 20, 3000).clip(0, 255)
    bright = rng.normal(190, 25, 2000).clip(0, 255)
    all_pixels = np.concatenate([dark, bright])

    counts, _bins, _bars = ax.hist(
        all_pixels, bins=64, color=GRAY3, edgecolor=GRAY5, linewidth=0.5
    )
    ax.axvline(
        x=128, color=RED_ACCENT, linewidth=2, linestyle="--", label="Próg Otsu T=128"
    )
    ax.fill_betweenx([0, max(counts) * 1.1], 0, 128, alpha=0.12, color=ACCENT)
    ax.fill_betweenx([0, max(counts) * 1.1], 128, 255, alpha=0.12, color=RED_ACCENT)
    ax.text(
        45,
        max(counts) * 0.85,
        "Klasa 0\n(tło)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        color=ACCENT,
    )
    ax.text(
        195,
        max(counts) * 0.85,
        "Klasa 1\n(obiekt)",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        color=RED_ACCENT,
    )
    ax.annotate(
        "Garb 1",
        xy=(60, max(counts) * 0.6),
        fontsize=FS_SMALL,
        ha="center",
        arrowprops={"arrowstyle": "->", "color": GRAY5},
        xytext=(30, max(counts) * 0.45),
    )
    ax.annotate(
        "Garb 2",
        xy=(190, max(counts) * 0.5),
        fontsize=FS_SMALL,
        ha="center",
        arrowprops={"arrowstyle": "->", "color": GRAY5},
        xytext=(220, max(counts) * 0.35),
    )
    ax.set_xlabel("Jasność piksela (0-255)", fontsize=FS)
    ax.set_ylabel("Liczba pikseli", fontsize=FS)
    ax.set_title("Histogram bimodalny", fontsize=FS_TITLE, fontweight="bold")
    ax.legend(fontsize=FS_SMALL, loc="upper right")
    ax.set_xlim(0, 255)

    # --- Panel 2: Within-class variance explanation ---
    _draw_otsu_variance_panel(axes[1])

    # --- Panel 3: Jednorodność explanation ---
    ax = axes[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title('"Jednorodne" = małe σ²', fontsize=FS_TITLE, fontweight="bold")

    # Draw two clusters
    # Good separation
    c0 = rng.normal(2, 0.4, 15)
    c1 = rng.normal(7, 0.4, 15)
    y_pos_0 = rng.uniform(6, 8, 15)
    y_pos_1 = rng.uniform(6, 8, 15)
    ax.scatter(c0, y_pos_0, c=ACCENT, s=30, zorder=5, label="Klasa 0")
    ax.scatter(c1, y_pos_1, c=RED_ACCENT, s=30, zorder=5, label="Klasa 1")
    ax.axvline(x=4.5, color=GREEN_ACCENT, linewidth=2, linestyle="--")
    ax.text(
        4.5,
        8.8,
        "T optymalny",
        ha="center",
        fontsize=FS_SMALL,
        color=GREEN_ACCENT,
        fontweight="bold",
    )
    ax.text(
        2, 5.3, "σ₀² mała\n(skupione)", ha="center", fontsize=FS_SMALL, color=ACCENT
    )
    ax.text(
        7, 5.3, "σ₁² mała\n(skupione)", ha="center", fontsize=FS_SMALL, color=RED_ACCENT
    )
    ax.text(
        5,
        4,
        "→ σ²_wewnątrz MINIMALNA\n→ klasy JEDNORODNE\n→ dobra segmentacja!",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        color=GREEN_ACCENT,
    )

    # Bad separation
    c0b = rng.normal(3.5, 1.5, 15)
    c1b = rng.normal(6, 1.5, 15)
    y_pos_0b = rng.uniform(1, 3, 15)
    y_pos_1b = rng.uniform(1, 3, 15)
    ax.scatter(c0b, y_pos_0b, c=ACCENT, s=30, marker="x", zorder=5)
    ax.scatter(c1b, y_pos_1b, c=RED_ACCENT, s=30, marker="x", zorder=5)
    ax.axvline(x=4.5, color=GRAY4, linewidth=1, linestyle=":", ymin=0, ymax=0.35)
    ax.text(
        5,
        0.3,
        "σ²_wewnątrz DUŻA → klasy mieszają się → zły próg",
        ha="center",
        fontsize=FS_SMALL,
        color=GRAY5,
    )

    ax.legend(fontsize=FS_SMALL, loc="upper left")

    _save_figure("q23_otsu_bimodal.png")


def _draw_watershed_result_panel(ax: Axes) -> None:
    """Draw panel 3: watershed result with over-segmentation problem."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Krok 3: wynik", fontsize=FS_TITLE, fontweight="bold")

    rect1 = FancyBboxPatch(
        (0.5, 6),
        3.5,
        3.2,
        boxstyle="round,pad=0.1",
        facecolor=ACCENT_LIGHT,
        edgecolor=BLACK,
        linewidth=1,
    )
    ax.add_patch(rect1)
    ax.text(2.25, 8.8, "Ideał: 2 segmenty", fontsize=FS, ha="center", fontweight="bold")
    ax.text(2.25, 7.5, "Segment A    Segment B", fontsize=FS_SMALL, ha="center")
    ax.text(
        2.25,
        6.7,
        "(po marker-controlled)",
        fontsize=FS_SMALL,
        ha="center",
        color=GREEN_ACCENT,
    )

    rect2 = FancyBboxPatch(
        (5.5, 6),
        4,
        3.2,
        boxstyle="round,pad=0.1",
        facecolor="#FFCDD2",
        edgecolor=BLACK,
        linewidth=1,
    )
    ax.add_patch(rect2)
    ax.text(
        7.5,
        8.8,
        "Problem: over-segmentation",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color=RED_ACCENT,
    )
    ax.text(
        7.5,
        7.8,
        "47 regionów zamiast 2!",
        fontsize=FS_SMALL,
        ha="center",
        color=RED_ACCENT,
    )
    ax.text(7.5, 7.1, "Każde mini-minimum", fontsize=FS_SMALL, ha="center")
    ax.text(7.5, 6.5, '→ osobna „dolina"', fontsize=FS_SMALL, ha="center")

    # Apply marker-controlled solution
    rect3 = FancyBboxPatch(
        (1, 0.5),
        8,
        4.5,
        boxstyle="round,pad=0.15",
        facecolor=GRAY1,
        edgecolor=GREEN_ACCENT,
        linewidth=1.5,
    )
    ax.add_patch(rect3)
    ax.text(
        5,
        4.3,
        "Rozwiązanie: Marker-controlled watershed",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        color=GREEN_ACCENT,
    )
    ax.text(
        5,
        3.4,
        '1. Zaznacz ręcznie „seeds" (markery) w każdym obiekcie',
        fontsize=FS_SMALL,
        ha="center",
    )
    ax.text(
        5,
        2.7,
        "2. Zalewaj TYLKO od tych markerów (nie od wszystkich minimów)",
        fontsize=FS_SMALL,
        ha="center",
    )
    ax.text(
        5,
        2.0,
        "3. Eliminuje fałszywe doliny z szumu",
        fontsize=FS_SMALL,
        ha="center",
    )
    ax.text(
        5,
        1.2,
        "Wynik: tyle segmentów, ile podano markerów",
        fontsize=FS_SMALL,
        ha="center",
        fontweight="bold",
    )


def generate_watershed() -> None:
    """Generate watershed."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))

    # --- Panel 1: Image as topographic surface ---
    ax = axes[0]
    x = np.linspace(0, 10, 200)
    # Create a surface with two valleys and a ridge
    surface = (
        3 * np.exp(-((x - 3) ** 2) / 1.5)
        + 4 * np.exp(-((x - 7) ** 2) / 1.2)
        + 0.5 * np.sin(x * 2)
        + 1
    )
    # Invert: valleys at objects (dark), peaks at boundaries (bright)
    surface_inv = 6 - surface + 1

    ax.fill_between(x, 0, surface_inv, color=GRAY2, alpha=0.7)
    ax.plot(x, surface_inv, color=BLACK, linewidth=1.5)

    # Mark valleys
    ax.annotate(
        "Dolina 1\n(obiekt A)",
        xy=(3, surface_inv[60]),
        fontsize=FS_SMALL,
        ha="center",
        va="bottom",
        arrowprops={"arrowstyle": "->", "color": ACCENT},
        xytext=(1.5, 5.5),
    )
    ax.annotate(
        "Dolina 2\n(obiekt B)",
        xy=(7, surface_inv[140]),
        fontsize=FS_SMALL,
        ha="center",
        va="bottom",
        arrowprops={"arrowstyle": "->", "color": RED_ACCENT},
        xytext=(8.5, 5.5),
    )
    # Mark ridge
    ax.annotate(
        "Grań\n(granica)",
        xy=(5, surface_inv[100]),
        fontsize=FS_SMALL,
        ha="center",
        va="bottom",
        arrowprops={"arrowstyle": "->", "color": GREEN_ACCENT},
        xytext=(5, 6.5),
    )

    ax.set_xlabel("Pozycja piksela", fontsize=FS)
    ax.set_ylabel("Jasność (= wysokość)", fontsize=FS)
    ax.set_title("Krok 1: obraz → teren", fontsize=FS_TITLE, fontweight="bold")
    ax.set_ylim(0, 7)

    # --- Panel 2: Flooding ---
    ax = axes[1]
    ax.fill_between(x, 0, surface_inv, color=GRAY2, alpha=0.7)
    ax.plot(x, surface_inv, color=BLACK, linewidth=1.5)

    # Water level
    water_level = 3.2

    # Fill water in valley 1
    x_v1 = x[(x > 1) & (x < _RIDGE_X)]
    s_v1 = surface_inv[(x > 1) & (x < _RIDGE_X)]
    ax.fill_between(
        x_v1, s_v1, water_level, where=s_v1 < water_level, color=ACCENT_LIGHT, alpha=0.6
    )
    # Fill water in valley 2
    x_v2 = x[(x > _RIDGE_X) & (x < _VALLEY2_END)]
    s_v2 = surface_inv[(x > _RIDGE_X) & (x < _VALLEY2_END)]
    ax.fill_between(
        x_v2, s_v2, water_level, where=s_v2 < water_level, color="#FFCDD2", alpha=0.6
    )

    ax.axhline(y=water_level, color=ACCENT, linewidth=1, linestyle="--", alpha=0.5)
    ax.text(3, 2.5, "Woda A", fontsize=FS, ha="center", color=ACCENT, fontweight="bold")
    ax.text(
        7, 2.2, "Woda B", fontsize=FS, ha="center", color=RED_ACCENT, fontweight="bold"
    )
    ax.annotate(
        "Tu się spotkają!\n→ GRANICA",
        xy=(5, surface_inv[100]),
        fontsize=FS_SMALL,
        ha="center",
        color=GREEN_ACCENT,
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "color": GREEN_ACCENT},
        xytext=(5, 6.2),
    )

    ax.set_xlabel("Pozycja piksela", fontsize=FS)
    ax.set_title("Krok 2: zalewanie", fontsize=FS_TITLE, fontweight="bold")
    ax.set_ylim(0, 7)

    # --- Panel 3: Result with problem ---
    _draw_watershed_result_panel(axes[2])

    _save_figure("q23_watershed.png")
