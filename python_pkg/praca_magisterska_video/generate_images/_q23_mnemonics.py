"""Mnemonic summary diagram generator."""

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
    GRAY5,
    GRAY6,
    GREEN_ACCENT,
    RED_ACCENT,
    _save_figure,
    plt,
)
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def generate_mnemonics() -> None:
    """Generate mnemonics."""
    _fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 16)
    ax.axis("off")
    ax.set_title(
        "Mnemoniki — segmentacja obrazu", fontsize=FS_TITLE + 2, fontweight="bold"
    )

    def draw_card(
        ax: Axes,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
        mnemonic: str,
        color: str,
        detail: str = "",
    ) -> None:
        """Draw card."""
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.15",
            facecolor=color,
            edgecolor=BLACK,
            linewidth=1,
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2,
            y + h - 0.3,
            title,
            ha="center",
            va="top",
            fontsize=FS,
            fontweight="bold",
        )
        ax.text(
            x + w / 2,
            y + h / 2 - 0.1,
            mnemonic,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            fontstyle="italic",
            color=GRAY6,
        )
        if detail:
            ax.text(
                x + w / 2,
                y + 0.4,
                detail,
                ha="center",
                va="bottom",
                fontsize=FS_TINY,
                color=GRAY5,
            )

    # Title: STRATEGIE KLASYCZNE
    ax.text(
        5,
        15.5,
        "STRATEGIE KLASYCZNE",
        fontsize=FS_TITLE,
        fontweight="bold",
        color=ACCENT,
        ha="center",
    )

    cards_classic = [
        (
            0.2,
            12.5,
            4.5,
            2.5,
            "Thresholding",
            '„PRÓG na bramce"\nPrzepuszcza > T,\nblokuje ≤ T',
            ACCENT_LIGHT,
            "jasne=1, ciemne=0",
        ),
        (
            5,
            12.5,
            4.5,
            2.5,
            "Otsu",
            '„AUTO-bramkarz"\nSam dobiera próg\nmin σ² wewnątrz',
            ACCENT_LIGHT,
            "histogram bimodalny",
        ),
        (
            0.2,
            9.5,
            4.5,
            2.5,
            "Region Growing",
            '„PLAMA rozlana"\nSeed → BFS po\npodobnych sąsiadach',
            ACCENT_LIGHT,
            "jak atrament na papierze",
        ),
        (
            5,
            9.5,
            4.5,
            2.5,
            "Watershed",
            '„ZALEWANIE terenu"\nDoliny=obiekty\nGranie=granice',
            ACCENT_LIGHT,
            "woda + geography",
        ),
        (
            0.2,
            6.5,
            4.5,
            2.5,
            "Mean Shift",
            '„KULKI toczą się"\nKażda → max gęstości\nBez K!',
            ACCENT_LIGHT,
            "bandwidth = okno",
        ),
        (
            5,
            6.5,
            4.5,
            2.5,
            "Normalized Cuts",
            '„CIĘCIE sznurków"\nGraf: tnij słabe\nkrawędzie (O(n³)!)',
            ACCENT_LIGHT,
            "eigenvector problem",
        ),
    ]

    for args in cards_classic:
        draw_card(ax, *args)

    # Title: SIECI NEURONOWE
    ax.text(
        15,
        15.5,
        "SIECI NEURONOWE",
        fontsize=FS_TITLE,
        fontweight="bold",
        color=GREEN_ACCENT,
        ha="center",
    )

    cards_nn = [
        (
            10.5,
            12.5,
            4.5,
            2.5,
            "FCN (2015)",
            '„FC → Conv 1x1"\nPierwsza end-to-end\nDowolny rozmiar',
            "#C8E6C9",
            "skip connections",
        ),
        (
            15.3,
            12.5,
            4.5,
            2.5,
            "U-Net (2015)",
            '„Litera U"\nEncoder↓ Decoder↑\nSkip = concat',
            "#C8E6C9",
            "medycyna, małe dane",
        ),
        (
            10.5,
            9.5,
            4.5,
            2.5,
            "DeepLab v3+",
            '„DZIURY w filtrze"\nAtrous conv (rate)\nASPP multi-scale',
            "#C8E6C9",
            "à trous = z dziurami",
        ),
        (
            15.3,
            9.5,
            4.5,
            2.5,
            "Transformer",
            '„WSZYSCY ze\nWSZYSTKIMI"\nSelf-attention O(n²)',
            "#C8E6C9",
            "SegFormer, Mask2Former",
        ),
    ]

    for args in cards_nn:
        draw_card(ax, *args)

    # Metryki
    ax.text(
        10,
        8.3,
        "METRYKI I LOSS",
        fontsize=FS_TITLE,
        fontweight="bold",
        color=RED_ACCENT,
        ha="center",
    )

    cards_metrics = [
        (
            10.5,
            6.5,
            4.5,
            1.6,
            "mIoU",
            '„Nakładka / Suma"\nIoU = A∩B / A\u222aB',
            "#FFCDD2",
            "",
        ),
        (
            15.3,
            6.5,
            4.5,
            1.6,
            "Dice / Focal",
            '„Dice=2·nakładka"\nFocal=trudne px',
            "#FFCDD2",
            "",
        ),
    ]

    for args in cards_metrics:
        draw_card(ax, *args)

    # Master mnemonic at bottom
    rect = FancyBboxPatch(
        (1, 0.3),
        18,
        5.5,
        boxstyle="round,pad=0.2",
        facecolor=GRAY1,
        edgecolor=BLACK,
        linewidth=1.5,
    )
    ax.add_patch(rect)
    ax.text(
        10,
        5.3,
        "SUPER-MNEMONIK: kolejność algorytmów segmentacji",
        ha="center",
        fontsize=FS,
        fontweight="bold",
    )
    ax.text(
        10,
        4.5,
        '„TORW-MN  FUD-T"',
        ha="center",
        fontsize=FS_TITLE + 2,
        fontweight="bold",
        color=RED_ACCENT,
    )
    ax.text(
        10,
        3.5,
        "Klasyczne: Thresholding → Otsu → Region"
        " growing → Watershed → Mean shift → Norm. cuts",
        ha="center",
        fontsize=FS_SMALL,
    )
    ax.text(
        10,
        2.8,
        "Neuronowe: FCN → U-Net → DeepLab → Transformer",
        ha="center",
        fontsize=FS_SMALL,
    )
    ax.text(
        10,
        1.8,
        "„Turyści Oglądają Rzekę, Wodospad,"
        " Morze, Nurt — Fotografują Uroczy"
        ' Dwór Tajemnic"',
        ha="center",
        fontsize=FS_SMALL,
        fontstyle="italic",
        color=ACCENT,
    )
    ax.text(
        10,
        1.0,
        "Klasyczne: proste→auto→BFS→flood→"
        "gęstość→graf   |   Neuronowe:"
        " FC→U-skip→dilated→attention",
        ha="center",
        fontsize=FS_TINY,
        color=GRAY5,
    )

    _save_figure("q23_mnemonics.png")
