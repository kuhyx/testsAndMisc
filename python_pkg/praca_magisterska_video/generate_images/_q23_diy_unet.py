"""DIY U-Net step-by-step diagram generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q23_common import (
    ACCENT,
    ACCENT_LIGHT,
    BLACK,
    FS,
    FS_SMALL,
    FS_TINY,
    GRAY1,
    GRAY3,
    GRAY5,
    GREEN_ACCENT,
    WHITE,
    _save_figure,
    np,
    plt,
    rng,
)
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _draw_unet_layer_stack(
    ax: Axes,
    layer_sizes: list[tuple[int, int]],
    *,
    face_color: str,
    edge_color: str,
    arrow_color: str,
    arrow_label: str,
    add_skip: bool = False,
) -> None:
    """Draw encoder or decoder layer stack for DIY U-Net."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    y_pos = 8.5
    for i, (s, c) in enumerate(layer_sizes):
        w = s / 64 * 4
        h = 0.8
        rect = FancyBboxPatch(
            (5 - w / 2, y_pos),
            w,
            h,
            boxstyle="round,pad=0.05",
            facecolor=face_color,
            edgecolor=edge_color,
            linewidth=1,
        )
        ax.add_patch(rect)
        label = f"{s}x{s}x{c}"
        if add_skip and i < len(layer_sizes) - 1:
            label += " + skip!"
        ax.text(
            5,
            y_pos + h / 2,
            label,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontweight="bold",
        )
        if i < len(layer_sizes) - 1:
            ax.annotate(
                "",
                xy=(5, y_pos - 0.3),
                xytext=(5, y_pos),
                arrowprops={
                    "arrowstyle": "->",
                    "color": arrow_color,
                    "lw": 1.5,
                },
            )
            ax.text(
                7,
                y_pos - 0.15,
                arrow_label,
                fontsize=FS_TINY,
                color=arrow_color,
            )
        y_pos -= 2.2


def _draw_unet_pseudocode(ax: Axes) -> None:
    """Draw panel 6: U-Net pseudocode."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Pseudokod U-Net", fontsize=FS, fontweight="bold")

    code_lines = [
        "# ENCODER",
        "e1 = conv_block(input, 64)   # 64x64",
        "e2 = conv_block(pool(e1), 128) # 32x32",
        "e3 = conv_block(pool(e2), 256) # 16x16",
        "",
        "# BOTTLENECK",
        "b = conv_block(pool(e3), 512)  # 8x8",
        "",
        "# DECODER + SKIP",
        "d3 = conv_block(concat(",
        "       upconv(b), e3), 256)   # 16x16",
        "d2 = conv_block(concat(",
        "       upconv(d3), e2), 128)  # 32x32",
        "d1 = conv_block(concat(",
        "       upconv(d2), e1), 64)   # 64x64",
        "",
        "output = conv_1x1(d1, n_classes)",
    ]
    for i, line in enumerate(code_lines):
        txt_color = (
            ACCENT
            if "concat" in line
            else (GREEN_ACCENT if "output" in line else BLACK)
        )
        ax.text(
            0.3,
            9.5 - i * 0.55,
            line,
            fontsize=FS_TINY,
            fontfamily="monospace",
            color=txt_color,
        )


def generate_diy_unet() -> None:
    """Generate diy unet."""
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))

    size = 64

    # Create synthetic image with two regions
    img = np.ones((size, size, 3), dtype=np.uint8) * 200  # bright bg
    # Dark region (object 1)
    yy, xx = np.mgrid[:size, :size]
    mask1 = ((xx - 20) ** 2 + (yy - 30) ** 2) < 12**2
    img[mask1] = [60, 60, 60]
    # Medium region (object 2)
    mask2 = ((xx - 45) ** 2 + (yy - 25) ** 2) < 8**2
    img[mask2] = [120, 120, 120]

    gt = np.zeros((size, size), dtype=np.uint8)
    gt[mask1] = 1  # class 1
    gt[mask2] = 2  # class 2

    # --- Panel 1: Input image ---
    ax = axes[0, 0]
    ax.imshow(img)
    ax.set_title("Krok 1: obraz RGB\n64x64x3", fontsize=FS, fontweight="bold")
    ax.axis("off")

    # --- Panel 2: Encoder shrinks ---
    ax = axes[0, 1]
    ax.set_title("Krok 2: Encoder ZMNIEJSZA", fontsize=FS, fontweight="bold")
    _draw_unet_layer_stack(
        ax,
        [(64, 3), (32, 64), (16, 128), (8, 256)],
        face_color=ACCENT_LIGHT,
        edge_color=ACCENT,
        arrow_color=ACCENT,
        arrow_label="Conv+Pool",
    )
    ax.text(
        5,
        0.3,
        "Wyciąga cechy:\nkrawędzie → tekstury → obiekty",
        ha="center",
        fontsize=FS_TINY,
        color=GRAY5,
    )

    # --- Panel 3: Bottleneck ---
    ax = axes[0, 2]
    # Show feature maps at bottleneck (abstract)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "Krok 3: Bottleneck\n(najbardziej abstrakcyjne cechy)",
        fontsize=FS,
        fontweight="bold",
    )

    # Show small abstract feature maps
    for k in range(4):
        small = rng.random((4, 4))
        ax_inset = fig.add_axes(
            [0.68 + (k % 2) * 0.08, 0.72 - (k // 2) * 0.1, 0.06, 0.06]
        )
        ax_inset.imshow(small, cmap="gray")
        ax_inset.axis("off")

    ax.text(
        5,
        5,
        '8x8x256\n\nMałe mapy, ale DUŻO kanałów\nKażdy kanał = jedna „cecha"\n'
        '(np. kanał 42 = „wykrył koło"\n  kanał 78 = „wykrył krawędź")\n\n'
        "Wie CO jest na obrazie\nale nie wie GDZIE dokładnie",
        ha="center",
        va="center",
        fontsize=FS_SMALL,
        bbox={"boxstyle": "round", "facecolor": GRAY1, "edgecolor": GRAY3},
    )

    # --- Panel 4: Decoder enlarges ---
    ax = axes[1, 0]
    ax.set_title(
        "Krok 4: Decoder ZWIĘKSZA\n(+ skip connections!)",
        fontsize=FS,
        fontweight="bold",
    )
    _draw_unet_layer_stack(
        ax,
        [(8, 256), (16, 128), (32, 64), (64, 3)],
        face_color="#C8E6C9",
        edge_color=GREEN_ACCENT,
        arrow_color=GREEN_ACCENT,
        arrow_label="UpConv+Concat",
        add_skip=True,
    )
    ax.text(
        5,
        0.3,
        "Odtwarza rozdzielczość:\nskip → przywraca krawędzie",
        ha="center",
        fontsize=FS_TINY,
        color=GRAY5,
    )

    # --- Panel 5: Output segmentation map ---
    ax = axes[1, 1]
    cmap = plt.cm.colors.ListedColormap([WHITE, ACCENT_LIGHT, "#FFCDD2"])
    ax.imshow(gt, cmap=cmap, interpolation="nearest")
    ax.set_title(
        "Krok 5: mapa segmentacji\n64x64 (3 klasy)", fontsize=FS, fontweight="bold"
    )
    ax.axis("off")
    ax.text(20, -3, "Tło=0, obiekt A=1, obiekt B=2", fontsize=FS_TINY, ha="center")

    # --- Panel 6: Summary pseudocode ---
    _draw_unet_pseudocode(axes[1, 2])

    _save_figure("q23_diy_unet.png")
