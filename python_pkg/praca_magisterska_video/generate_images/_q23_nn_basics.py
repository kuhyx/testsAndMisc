"""ReLU and dot product diagram generators."""

from __future__ import annotations

from _q23_common import (
    ACCENT,
    ACCENT_LIGHT,
    BLACK,
    FS,
    FS_SMALL,
    FS_TINY,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY5,
    GREEN_ACCENT,
    RED_ACCENT,
    _save_figure,
    np,
    plt,
)
from matplotlib import patches


def generate_relu() -> None:
    """Generate relu."""
    _fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))

    # --- Panel 1: ReLU plot ---
    ax = axes[0]
    x = np.linspace(-5, 5, 200)
    relu = np.maximum(0, x)
    ax.plot(x, relu, color=ACCENT, linewidth=2.5, label="ReLU(x) = max(0, x)")
    ax.axhline(y=0, color=GRAY3, linewidth=0.5)
    ax.axvline(x=0, color=GRAY3, linewidth=0.5)
    ax.fill_between(x[x < 0], 0, 0, color=RED_ACCENT, alpha=0.1)
    ax.fill_between(x[x >= 0], 0, relu[x >= 0], color=ACCENT, alpha=0.1)

    # Annotations
    ax.annotate(
        'x < 0 → output = 0\n(neuron „wyłączony")',
        xy=(-3, 0),
        fontsize=FS_SMALL,
        ha="center",
        va="bottom",
        color=RED_ACCENT,
        arrowprops={"arrowstyle": "->", "color": RED_ACCENT},
        xytext=(-3, 2),
    )
    ax.annotate(
        'x ≥ 0 → output = x\n(neuron „włączony")',
        xy=(3, 3),
        fontsize=FS_SMALL,
        ha="center",
        va="bottom",
        color=ACCENT,
        arrowprops={"arrowstyle": "->", "color": ACCENT},
        xytext=(3, 4.5),
    )
    ax.scatter([0], [0], c=BLACK, s=40, zorder=5)
    ax.text(0.3, -0.5, "(0,0)", fontsize=FS_SMALL, color=GRAY5)
    ax.set_xlabel("x (wejście neuronu)", fontsize=FS)
    ax.set_ylabel("ReLU(x)", fontsize=FS)
    ax.set_title("ReLU — Rectified Linear Unit", fontsize=FS_TITLE, fontweight="bold")
    ax.legend(fontsize=FS_SMALL, loc="upper left")
    ax.set_ylim(-1, 6)
    ax.grid(visible=True, alpha=0.2)

    # --- Panel 2: Why ReLU ---
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Dlaczego ReLU?", fontsize=FS_TITLE, fontweight="bold")

    y = 9.0
    lines = [
        ("Neuron oblicza:", FS, BLACK, "bold"),
        ("  z = w₁·x₁ + w₂·x₂ + ... + bias", FS_SMALL, BLACK, "normal"),
        ("  output = ReLU(z) = max(0, z)", FS_SMALL, ACCENT, "bold"),
        ("", 0, "", ""),
        ("Przykład:", FS, BLACK, "bold"),
        ("  wagi: w₁=0.5, w₂=-0.3, bias=0.1", FS_SMALL, BLACK, "normal"),
        ("  wejścia: x₁=2.0, x₂=4.0", FS_SMALL, BLACK, "normal"),
        ("  z = 0.5·2 + (-0.3)·4 + 0.1 = -0.1", FS_SMALL, BLACK, "normal"),
        ("  ReLU(-0.1) = max(0, -0.1) = 0", FS_SMALL, RED_ACCENT, "bold"),
        ("  → neuron milczy (wejście nieistotne)", FS_SMALL, GRAY5, "normal"),
        ("", 0, "", ""),
        ("Gdyby z = 2.3:", FS, BLACK, "bold"),
        ("  ReLU(2.3) = max(0, 2.3) = 2.3", FS_SMALL, GREEN_ACCENT, "bold"),
        ("  → neuron aktywny! Przekazuje sygnał", FS_SMALL, GRAY5, "normal"),
        ("", 0, "", ""),
        ("Szybsza niż sigmoid/tanh", FS_SMALL, GRAY5, "normal"),
        ("(brak exp() → szybkie obliczenia)", FS_SMALL, GRAY5, "normal"),
    ]
    for txt, size, color, weight in lines:
        if txt == "":
            y -= 0.2
            continue
        ax.text(0.5, y, txt, fontsize=size, color=color, fontweight=weight, va="top")
        y -= 0.5

    _save_figure("q23_relu.png")


def generate_dot_product() -> None:
    """Generate dot product."""
    _fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))

    # --- Panel 1: Concept ---
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "Iloczyn skalarny\n(dot product)", fontsize=FS_TITLE, fontweight="bold"
    )

    y = 8.5
    lines = [
        ("Dwa wektory (listy liczb) → JEDNA liczba", FS, BLACK, "bold"),
        ("", 0, "", ""),
        ("a = [a₁, a₂, a₃]    b = [b₁, b₂, b₃]", FS, ACCENT, "normal"),
        ("", 0, "", ""),
        ("a · b = a₁·b₁ + a₂·b₂ + a₃·b₃", FS, BLACK, "bold"),
        ("", 0, "", ""),
        ("Przykład:", FS, BLACK, "bold"),
        ("a = [1, 3, -2]    b = [4, -1, 5]", FS_SMALL, BLACK, "normal"),
        ("a·b = 1·4 + 3·(-1) + (-2)·5", FS_SMALL, BLACK, "normal"),
        ("    = 4 + (-3) + (-10) = -9", FS_SMALL, RED_ACCENT, "bold"),
        ("", 0, "", ""),
        (
            'Duży wynik → wektory „podobne" (w tym samym kierunku)',
            FS_SMALL,
            GREEN_ACCENT,
            "normal",
        ),
        ('Mały/ujemny → wektory „różne"', FS_SMALL, RED_ACCENT, "normal"),
    ]
    for txt, size, color, weight in lines:
        if txt == "":
            y -= 0.25
            continue
        ax.text(0.5, y, txt, fontsize=size, color=color, fontweight=weight, va="top")
        y -= 0.55

    # --- Panel 2: Convolution as dot product ---
    ax = axes[1]
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_aspect("equal")
    ax.set_title(
        "Konwolucja = iloczyn skalarny\nfiltra x fragment obrazu",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    # Filter 3x3
    filter_vals = [[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]]
    for i in range(3):
        for j in range(3):
            rect = patches.Rectangle(
                (j - 0.4, 4 - i - 0.4),
                0.8,
                0.8,
                facecolor=ACCENT_LIGHT,
                edgecolor=BLACK,
                linewidth=0.8,
            )
            ax.add_patch(rect)
            ax.text(
                j,
                4 - i,
                str(filter_vals[i][j]),
                ha="center",
                va="center",
                fontsize=FS,
                fontweight="bold",
            )

    ax.text(1, 1.5, "Filtr", ha="center", fontsize=FS, fontweight="bold", color=ACCENT)

    # Image patch
    img_vals = [[50, 50, 200], [50, 50, 200], [50, 50, 200]]
    for i in range(3):
        for j in range(3):
            rect = patches.Rectangle(
                (j + 2.6, 4 - i - 0.4),
                0.8,
                0.8,
                facecolor=GRAY2,
                edgecolor=BLACK,
                linewidth=0.8,
            )
            ax.add_patch(rect)
            ax.text(
                j + 3,
                4 - i,
                str(img_vals[i][j]),
                ha="center",
                va="center",
                fontsize=FS,
                fontweight="bold",
            )

    ax.text(
        4,
        1.5,
        "Fragment\nobrazu",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        color=GRAY5,
    )

    ax.text(
        2.5,
        0.5,
        "(-1)·50 + 0·50 + 1·200 +\n"
        "(-1)·50 + 0·50 + 1·200 +\n"
        "(-1)·50 + 0·50 + 1·200\n= 450 (krawędź!)",
        ha="center",
        fontsize=FS_TINY,
        fontweight="bold",
        bbox={"boxstyle": "round", "facecolor": GRAY1, "edgecolor": GREEN_ACCENT},
    )

    ax.axis("off")

    # --- Panel 3: Vector visualization ---
    ax = axes[2]
    # Draw two vectors
    ax.quiver(
        0,
        0,
        3,
        4,
        angles="xy",
        scale_units="xy",
        scale=1,
        color=ACCENT,
        width=0.025,
        label="a = [3, 4]",
    )
    ax.quiver(
        0,
        0,
        4,
        1,
        angles="xy",
        scale_units="xy",
        scale=1,
        color=RED_ACCENT,
        width=0.025,
        label="b = [4, 1]",
    )

    # Show angle
    theta = np.linspace(np.arctan2(1, 4), np.arctan2(4, 3), 30)
    r = 1.5
    ax.plot(r * np.cos(theta), r * np.sin(theta), color=GREEN_ACCENT, linewidth=1.5)
    ax.text(1.8, 1.3, "θ", fontsize=FS, color=GREEN_ACCENT, fontweight="bold")

    ax.text(3.2, 4.2, "a", fontsize=FS, color=ACCENT, fontweight="bold")
    ax.text(4.2, 1.2, "b", fontsize=FS, color=RED_ACCENT, fontweight="bold")

    ax.text(
        2.5,
        -1.0,
        "a · b = |a|·|b|·cos(θ)\n= 3·4 + 4·1 = 16",
        ha="center",
        fontsize=FS_SMALL,
        fontweight="bold",
        bbox={"boxstyle": "round", "facecolor": GRAY1, "edgecolor": GRAY3},
    )
    ax.text(
        2.5,
        -2.0,
        'Mały kąt θ → duży dot product\n= wektory „zgadają się"',
        ha="center",
        fontsize=FS_TINY,
        color=GRAY5,
    )

    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-2.5, 5.5)
    ax.set_aspect("equal")
    ax.grid(visible=True, alpha=0.2)
    ax.legend(fontsize=FS_SMALL, loc="upper left")
    ax.set_title("Geometrycznie: kąt", fontsize=FS_TITLE, fontweight="bold")

    _save_figure("q23_dot_product.png")
