"""C4 Model diagram generation (4 zoom levels)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    OUTPUT_DIR,
    _draw_class,
    draw_arrow,
    draw_box,
    draw_line,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)


def _draw_c4_system_context(ax1: Axes) -> None:
    """Draw C4 Level 1: System Context."""
    # Person
    ax1.add_patch(
        plt.Circle(
            (20, 55),
            4,
            lw=1.5,
            edgecolor=LN,
            facecolor=GRAY1,
        )
    )
    # Head
    ax1.add_patch(
        plt.Circle(
            (20, 57.5),
            1.5,
            lw=1.2,
            edgecolor=LN,
            facecolor="white",
        )
    )
    # Body
    draw_line(ax1, 20, 56, 20, 52.5, lw=1.2)
    draw_line(ax1, 17, 55, 23, 55, lw=1.2)
    ax1.text(
        20,
        48,
        "Klient",
        ha="center",
        fontsize=8,
        fontweight="bold",
    )

    draw_box(
        ax1,
        38,
        43,
        24,
        18,
        "System\nE-commerce",
        fill=GRAY2,
        lw=2,
        fontsize=9,
        fontweight="bold",
        rounded=True,
    )

    draw_box(
        ax1,
        72,
        48,
        20,
        12,
        "System\nP\u0142atno\u015bci\n(zewn.)",
        fill=GRAY4,
        lw=1.5,
        fontsize=7,
        rounded=True,
    )
    ax1.add_patch(
        plt.Rectangle(
            (72, 48),
            20,
            12,
            lw=1.5,
            edgecolor=LN,
            facecolor="none",
            linestyle="--",
        )
    )

    draw_arrow(ax1, 24, 54, 38, 54)
    ax1.text(
        31,
        56,
        "sk\u0142ada\nzam\u00f3wienia",
        fontsize=6,
        ha="center",
    )
    draw_arrow(ax1, 62, 54, 72, 54)
    ax1.text(67, 56, "API", fontsize=6, ha="center")

    ax1.text(
        50,
        20,
        "Kto u\u017cywa systemu?\nZ czym si\u0119 integruje?",
        ha="center",
        fontsize=7,
        fontstyle="italic",
        bbox={
            "boxstyle": "round",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.5,
        },
    )


def _draw_c4_container(ax2: Axes) -> None:
    """Draw C4 Level 2: Container."""
    ax2.add_patch(
        plt.Rectangle(
            (5, 15),
            90,
            58,
            lw=1.5,
            edgecolor=LN,
            facecolor="none",
            linestyle="--",
        )
    )
    ax2.text(
        50,
        75,
        "System E-commerce",
        ha="center",
        fontsize=8,
        fontweight="bold",
        fontstyle="italic",
    )

    containers = [
        ("SPA\n(React)", 15, 50, 18, 12, GRAY1),
        ("API\nServer\n(Node.js)", 42, 50, 18, 12, GRAY2),
        ("Database\n(PostgreSQL)", 70, 50, 18, 12, GRAY3),
        ("Worker\n(Python)", 42, 25, 18, 12, GRAY1),
    ]
    for label, x, y, w, h, fill in containers:
        draw_box(
            ax2,
            x,
            y,
            w,
            h,
            label,
            fill=fill,
            lw=1.5,
            fontsize=7,
            fontweight="bold",
            rounded=True,
        )

    draw_arrow(ax2, 33, 56, 42, 56)
    ax2.text(37.5, 58, "REST", fontsize=6, ha="center")
    draw_arrow(ax2, 60, 56, 70, 56)
    ax2.text(65, 58, "SQL", fontsize=6, ha="center")
    draw_arrow(ax2, 51, 50, 51, 37)
    ax2.text(53, 44, "async", fontsize=6)

    ax2.text(
        50,
        8,
        "Jakie kontenery techniczne\nsk\u0142adaj\u0105 si\u0119 na system?",
        ha="center",
        fontsize=7,
        fontstyle="italic",
        bbox={
            "boxstyle": "round",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.5,
        },
    )


def _draw_c4_component(ax3: Axes) -> None:
    """Draw C4 Level 3: Component."""
    ax3.add_patch(
        plt.Rectangle(
            (5, 15),
            90,
            58,
            lw=1.5,
            edgecolor=LN,
            facecolor="none",
            linestyle="--",
        )
    )
    ax3.text(
        50,
        75,
        "API Server (Node.js)",
        ha="center",
        fontsize=8,
        fontweight="bold",
        fontstyle="italic",
    )

    components = [
        ("OrderController", 10, 50, 22, 10, GRAY1),
        ("AuthService", 40, 50, 22, 10, GRAY2),
        ("PaymentGateway\n(adapter)", 70, 50, 22, 10, GRAY1),
        ("OrderRepository", 25, 25, 22, 10, GRAY2),
        ("NotificationService", 57, 25, 22, 10, GRAY1),
    ]
    for label, x, y, w, h, fill in components:
        draw_box(
            ax3,
            x,
            y,
            w,
            h,
            label,
            fill=fill,
            lw=1.5,
            fontsize=6.5,
            fontweight="bold",
            rounded=True,
        )

    draw_arrow(ax3, 32, 55, 40, 55)
    draw_arrow(ax3, 62, 55, 70, 55)
    draw_arrow(ax3, 21, 50, 30, 35)
    draw_arrow(ax3, 51, 50, 62, 35)

    ax3.text(
        50,
        8,
        "Jakie modu\u0142y/komponenty\nwewn\u0105trz kontenera?",
        ha="center",
        fontsize=7,
        fontstyle="italic",
        bbox={
            "boxstyle": "round",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.5,
        },
    )


def _draw_c4_code(ax4: Axes) -> None:
    """Draw C4 Level 4: Code (UML)."""
    _draw_class(
        ax4,
        5,
        40,
        "\u00abinterface\u00bb\nIOrderRepository",
        [],
        ["+save(order)", "+findById(id)"],
        w=32,
        fill=GRAY4,
    )
    _draw_class(
        ax4,
        55,
        40,
        "OrderRepository",
        ["-db: Database"],
        ["+save(order)", "+findById(id)"],
        w=32,
        fill=GRAY1,
    )
    _draw_class(
        ax4,
        30,
        10,
        "Order",
        ["-id: UUID", "-items: List", "-total: Money"],
        ["+addItem(item)", "+calculateTotal()"],
        w=32,
        fill=GRAY2,
    )

    ax4.annotate(
        "",
        xy=(37, 46),
        xytext=(55, 50),
        arrowprops={
            "arrowstyle": "-|>",
            "color": LN,
            "lw": 1.2,
            "linestyle": "--",
        },
    )
    ax4.text(
        46,
        52,
        "\u00abimplements\u00bb",
        fontsize=6,
        ha="center",
        fontstyle="italic",
    )

    draw_arrow(ax4, 71, 40, 50, 24)
    ax4.text(64, 32, "uses", fontsize=6, fontstyle="italic")

    ax4.text(
        50,
        3,
        "Diagramy klas UML\n(opcjonalny poziom szczeg\u00f3\u0142owo\u015bci)",
        ha="center",
        fontsize=7,
        fontstyle="italic",
        bbox={
            "boxstyle": "round",
            "facecolor": GRAY4,
            "edgecolor": LN,
            "lw": 0.5,
        },
    )


def generate_c4() -> None:
    """Generate c4."""
    fig, axes = plt.subplots(2, 2, figsize=(8.27, 10))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        "C4 Model (Simon Brown) \u2014 4 poziomy zoomu",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=0.98,
    )

    titles = [
        "Level 1: System Context",
        "Level 2: Container",
        "Level 3: Component",
        "Level 4: Code (UML)",
    ]

    for idx, ax_item in enumerate(axes.flat):
        ax_item.set_xlim(0, 100)
        ax_item.set_ylim(0, 80)
        ax_item.set_aspect("equal")
        ax_item.axis("off")
        ax_item.set_title(
            titles[idx],
            fontsize=10,
            fontweight="bold",
            pad=8,
        )

    _draw_c4_system_context(axes[0, 0])
    _draw_c4_container(axes[0, 1])
    _draw_c4_component(axes[1, 0])
    _draw_c4_code(axes[1, 1])

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(
        str(Path(OUTPUT_DIR) / "c4_model.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK C4 Model")
