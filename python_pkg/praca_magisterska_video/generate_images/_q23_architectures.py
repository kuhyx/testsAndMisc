"""FCN and U-Net architecture diagram generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    GRAY5,
    GREEN_ACCENT,
    RED_ACCENT,
    _save_figure,
    plt,
)
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def generate_fcn() -> None:
    """Generate fcn."""
    _fig, axes = plt.subplots(2, 1, figsize=(10, 7))

    # --- Panel 1: FC vs Conv 1x1 ---
    ax = axes[0]
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title(
        "FC (Fully Connected) vs Conv 1x1", fontsize=FS_TITLE, fontweight="bold"
    )

    # Classic CNN with FC
    layer_info_fc = [
        (1.5, "Obraz\n224x224x3", 2.2, GRAY2),
        (4.5, "Conv+Pool\n112x112x64", 1.8, GRAY2),
        (7.5, "Conv+Pool\n7x7x512", 1.0, GRAY2),
        (10, "Flatten\n25088", 0.5, ACCENT_LIGHT),
        (12, "FC\n4096", 0.5, ACCENT_LIGHT),
        (14, "FC\n1000", 0.3, ACCENT_LIGHT),
        (16, '"Kot"', 0.3, "#FFCDD2"),
    ]

    y_fc = 4.5
    for i, (x, label, w, color) in enumerate(layer_info_fc):
        rect = FancyBboxPatch(
            (x - w / 2, y_fc - 0.6),
            w,
            1.2,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor=BLACK,
            linewidth=0.8,
        )
        ax.add_patch(rect)
        ax.text(x, y_fc, label, ha="center", va="center", fontsize=FS_TINY)
        if i < len(layer_info_fc) - 1:
            next_x = layer_info_fc[i + 1][0]
            ax.annotate(
                "",
                xy=(next_x - layer_info_fc[i + 1][2] / 2, y_fc),
                xytext=(x + w / 2, y_fc),
                arrowprops={"arrowstyle": "->", "color": GRAY5, "lw": 1},
            )

    ax.text(
        0.3, y_fc, "CNN:", fontsize=FS, fontweight="bold", color=RED_ACCENT, va="center"
    )
    ax.text(
        12,
        y_fc + 1,
        "PROBLEM: FC wymaga\nSTAŁEGO rozmiaru\n(np. 224x224)",
        ha="center",
        fontsize=FS_SMALL,
        color=RED_ACCENT,
        fontweight="bold",
        bbox={
            "boxstyle": "round",
            "facecolor": "#FFCDD2",
            "edgecolor": RED_ACCENT,
            "alpha": 0.3,
        },
    )

    # FCN with Conv 1x1
    layer_info_fcn = [
        (1.5, "Obraz\nHxWx3", 2.2, GRAY2),
        (4.5, "Conv+Pool\nH/2 x W/2\nx64", 1.8, GRAY2),
        (7.5, "Conv+Pool\nH/32 x W/32\nx512", 1.0, GRAY2),
        (10.5, "Conv 1x1\nH/32 x W/32\nxC", 0.8, "#C8E6C9"),
        (13.5, "Upsample\nHxWxC", 1.8, "#C8E6C9"),
        (16.5, "Mapa\nsegmentacji", 1.5, "#C8E6C9"),
    ]

    y_fcn = 1.5
    for i, (x, label, w, color) in enumerate(layer_info_fcn):
        rect = FancyBboxPatch(
            (x - w / 2, y_fcn - 0.7),
            w,
            1.4,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor=BLACK,
            linewidth=0.8,
        )
        ax.add_patch(rect)
        ax.text(x, y_fcn, label, ha="center", va="center", fontsize=FS_TINY)
        if i < len(layer_info_fcn) - 1:
            next_x = layer_info_fcn[i + 1][0]
            ax.annotate(
                "",
                xy=(next_x - layer_info_fcn[i + 1][2] / 2, y_fcn),
                xytext=(x + w / 2, y_fcn),
                arrowprops={"arrowstyle": "->", "color": GRAY5, "lw": 1},
            )

    ax.text(
        0.3,
        y_fcn,
        "FCN:",
        fontsize=FS,
        fontweight="bold",
        color=GREEN_ACCENT,
        va="center",
    )
    ax.text(
        10.5,
        y_fcn + 1.2,
        "Conv 1x1:\nkażdy piksel\nosobno x wagi\n(jak FC ale\nzachowuje HxW)",
        ha="center",
        fontsize=FS_TINY,
        color=GREEN_ACCENT,
        bbox={
            "boxstyle": "round",
            "facecolor": "#C8E6C9",
            "edgecolor": GREEN_ACCENT,
            "alpha": 0.3,
        },
    )

    # --- Panel 2: What FC and Conv do ---
    ax = axes[1]
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title(
        "Co robi warstwa FC? Co robi konwolucja?", fontsize=FS_TITLE, fontweight="bold"
    )

    # FC explanation
    rect = FancyBboxPatch(
        (0.3, 3.2),
        9,
        2.5,
        boxstyle="round,pad=0.15",
        facecolor=ACCENT_LIGHT,
        edgecolor=ACCENT,
        linewidth=1,
    )
    ax.add_patch(rect)
    ax.text(
        4.8, 5.2, "Fully Connected (FC)", fontsize=FS, fontweight="bold", ha="center"
    )
    ax.text(
        4.8,
        4.5,
        "KAŻDY neuron połączony z KAŻDYM wejściem\n"
        "25 088 wejść x 4 096 neuronów = ~103 MLN wag!\n"
        "Traci informację GDZIE (przestrzenną)\n"
        "Wymaga STAŁEGO rozmiaru wejścia",
        fontsize=FS_TINY,
        ha="center",
        va="top",
    )

    # Conv explanation
    rect = FancyBboxPatch(
        (10.3, 3.2),
        9,
        2.5,
        boxstyle="round,pad=0.15",
        facecolor="#C8E6C9",
        edgecolor=GREEN_ACCENT,
        linewidth=1,
    )
    ax.add_patch(rect)
    ax.text(14.8, 5.2, "Konwolucja (Conv)", fontsize=FS, fontweight="bold", ha="center")
    ax.text(
        14.8,
        4.5,
        'Filtr (np. 3x3) „jedzie" po obrazie\n'
        "Te same wagi dla KAŻDEJ pozycji\n"
        "Zachowuje informację GDZIE\n"
        "Akceptuje DOWOLNY rozmiar wejścia",
        fontsize=FS_TINY,
        ha="center",
        va="top",
    )

    # Conv 1x1 explanation
    rect = FancyBboxPatch(
        (3, 0.3),
        14,
        2.2,
        boxstyle="round,pad=0.15",
        facecolor=GRAY1,
        edgecolor=BLACK,
        linewidth=1,
    )
    ax.add_patch(rect)
    ax.text(
        10,
        2.1,
        'Conv 1x1 = „FC per piksel"',
        fontsize=FS,
        fontweight="bold",
        ha="center",
    )
    ax.text(
        10,
        1.5,
        "Filtr 1x1: patrzy na JEDEN piksel, ale WSZYSTKIE kanały (512→C klas)\n"
        "Działa jak FC ale zachowuje mapę HxW → każdy piksel osobno klasyfikowany\n"
        "FCN: zamień FC na Conv1x1 → koniec z wymogiem stałego rozmiaru!",
        fontsize=FS_TINY,
        ha="center",
        va="top",
    )

    _save_figure("q23_fc_vs_conv1x1.png")


def generate_unet() -> None:
    """Generate unet."""
    _fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(-1, 21)
    ax.set_ylim(-1, 12)
    ax.axis("off")
    ax.set_title(
        "U-Net: architektura w kształcie litery U",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
    )

    # Encoder layers (going DOWN-LEFT)
    encoder_layers = [
        (2, 10, 2.5, 1.5, "572x572x1\n(wejście)", 64),
        (2, 7.5, 2.2, 1.3, "284x284\nx64", 64),
        (2, 5, 1.8, 1.1, "140x140\nx128", 128),
        (2, 2.5, 1.5, 1.0, "68x68\nx256", 256),
    ]

    # Bottleneck
    bottleneck = (8, 0.5, 2.5, 1.2, "32x32x512\n(bottleneck)", 512)

    # Decoder layers (going UP-RIGHT)
    decoder_layers = [
        (14, 2.5, 1.5, 1.0, "68x68\nx256", 256),
        (14, 5, 1.8, 1.1, "140x140\nx128", 128),
        (14, 7.5, 2.2, 1.3, "284x284\nx64", 64),
        (14, 10, 2.5, 1.5, "572x572xC\n(mapa seg.)", "C"),
    ]

    def draw_block(
        ax: Axes,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        color: str,
    ) -> None:
        """Draw block."""
        rect = FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor=BLACK,
            linewidth=1.2,
        )
        ax.add_patch(rect)
        ax.text(x, y, label, ha="center", va="center", fontsize=FS_TINY)

    # Draw encoder
    for x, y, w, h, label, _channels in encoder_layers:
        draw_block(ax, x, y, w, h, label, ACCENT_LIGHT)

    # Draw arrows down (encoder)
    for i in range(len(encoder_layers) - 1):
        x1, y1 = encoder_layers[i][0], encoder_layers[i][1] - encoder_layers[i][3] / 2
        x2, y2 = (
            encoder_layers[i + 1][0],
            encoder_layers[i + 1][1] + encoder_layers[i + 1][3] / 2,
        )
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops={"arrowstyle": "->", "color": ACCENT, "lw": 2},
        )
        ax.text(
            x1 - 1.7,
            (y1 + y2) / 2,
            "MaxPool\n2x2\n↓ zmniejsz",
            fontsize=FS_TINY,
            ha="center",
            color=ACCENT,
            fontweight="bold",
        )

    # Encoder to bottleneck
    x1, y1 = encoder_layers[-1][0], encoder_layers[-1][1] - encoder_layers[-1][3] / 2
    draw_block(
        ax,
        bottleneck[0],
        bottleneck[1],
        bottleneck[2],
        bottleneck[3],
        bottleneck[4],
        GRAY2,
    )
    ax.annotate(
        "",
        xy=(bottleneck[0] - bottleneck[2] / 2, bottleneck[1] + bottleneck[3] / 2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "color": ACCENT, "lw": 2},
    )

    # Bottleneck to decoder
    ax.annotate(
        "",
        xy=(
            decoder_layers[0][0] - decoder_layers[0][2] / 2,
            decoder_layers[0][1] - decoder_layers[0][3] / 2,
        ),
        xytext=(bottleneck[0] + bottleneck[2] / 2, bottleneck[1] + bottleneck[3] / 2),
        arrowprops={"arrowstyle": "->", "color": RED_ACCENT, "lw": 2},
    )

    # Draw decoder
    for x, y, w, h, label, channels in decoder_layers:
        color = "#C8E6C9" if channels != "C" else "#A5D6A7"
        draw_block(ax, x, y, w, h, label, color)

    # Draw arrows up (decoder)
    for i in range(len(decoder_layers) - 1):
        x1, y1 = decoder_layers[i][0], decoder_layers[i][1] + decoder_layers[i][3] / 2
        x2, y2 = (
            decoder_layers[i + 1][0],
            decoder_layers[i + 1][1] - decoder_layers[i + 1][3] / 2,
        )
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops={"arrowstyle": "->", "color": GREEN_ACCENT, "lw": 2},
        )
        ax.text(
            x1 + 2,
            (y1 + y2) / 2,
            "UpConv\n2x2\n↑ zwiększ",
            fontsize=FS_TINY,
            ha="center",
            color=GREEN_ACCENT,
            fontweight="bold",
        )

    # Skip connections (horizontal arrows)
    for i in range(len(encoder_layers)):
        enc = encoder_layers[i]
        dec = decoder_layers[len(decoder_layers) - 1 - i]
        ax.annotate(
            "",
            xy=(dec[0] - dec[2] / 2, dec[1]),
            xytext=(enc[0] + enc[2] / 2, enc[1]),
            arrowprops={
                "arrowstyle": "->",
                "color": GRAY5,
                "lw": 1.5,
                "linestyle": "dashed",
            },
        )
        mid_x = (enc[0] + enc[2] / 2 + dec[0] - dec[2] / 2) / 2
        ax.text(
            mid_x,
            enc[1] + 0.6,
            "skip\n(concat)",
            fontsize=FS_TINY,
            ha="center",
            color=GRAY5,
            fontweight="bold",
        )

    # Labels
    ax.text(
        0,
        11.5,
        "ENCODER\n(↓ zmniejsza)",
        fontsize=FS,
        fontweight="bold",
        color=ACCENT,
        ha="center",
    )
    ax.text(
        17,
        11.5,
        "DECODER\n(↑ zwiększa)",
        fontsize=FS,
        fontweight="bold",
        color=GREEN_ACCENT,
        ha="center",
    )
    ax.text(
        8,
        -0.8,
        'Kształt litery „U": encoder schodzi ↓ → bottleneck na dnie → decoder wraca ↑',
        fontsize=FS_SMALL,
        ha="center",
        color=GRAY5,
        fontweight="bold",
    )

    # Concatenation explanation
    rect = FancyBboxPatch(
        (17.5, 3),
        3,
        5,
        boxstyle="round,pad=0.15",
        facecolor=GRAY1,
        edgecolor=GRAY5,
        linewidth=1,
        linestyle="--",
    )
    ax.add_patch(rect)
    ax.text(
        19, 7.5, "Concatenation:", fontsize=FS_SMALL, ha="center", fontweight="bold"
    )
    ax.text(
        19,
        6.5,
        "Encoder: 64 kanały\nDecoder: 64 kanały\n→ concat → 128 kanałów\n\n"
        "Jak sklejenie\ndwóch stosów\nkart:",
        fontsize=FS_TINY,
        ha="center",
    )
    ax.text(
        19,
        3.7,
        "[enc₁|enc₂|...|dec₁|dec₂|...]",
        fontsize=FS_TINY - 1,
        ha="center",
        fontweight="bold",
        color=ACCENT,
    )

    _save_figure("q23_unet_arch.png")
