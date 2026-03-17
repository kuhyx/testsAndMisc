"""Consensus and distributed systems diagrams."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_study_diagrams import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OUTPUT_DIR,
    draw_arrow,
    draw_box,
)

_logger = logging.getLogger(__name__)


def draw_linearizability_vs_sequential() -> None:
    """Draw linearizability vs sequential."""
    _fig, axes = plt.subplots(2, 1, figsize=(8.27, 5.5))

    for _i, (ax, title, subtitle, operations, result_text) in enumerate(
        zip(
            axes,
            ["Linearizability", "Sequential Consistency"],
            [
                'Operacja „wygląda" atomowo w czasie rzeczywistym',
                "Globalny porządek zgodny z programem, ale NIE z czasem rzeczywistym",
            ],
            [
                # Linearizability
                [
                    ("Klient A", 1, 3, "write(x,1)", GRAY1),
                    ("Klient B", 2, 4, "read(x)→1 ✓", GRAY2),
                    ("Klient A", 5, 7, "write(x,2)", GRAY1),
                ],
                # Sequential consistency
                [
                    ("Klient A", 1, 3, "write(x,1)", GRAY1),
                    ("Klient B", 2, 4, "read(x)→0 ✓", GRAY2),
                    ("Klient A", 5, 7, "write(x,2)", GRAY1),
                ],
            ],
            [
                "read MUSI zwrócić 1 (write zakończony w czasie rzeczywistym)",
                "read MOŻE zwrócić 0 (globalny porządek: read, write(1), write(2))",
            ],
            strict=False,
        )
    ):
        ax.set_xlim(0, 9)
        ax.set_ylim(-0.5, 3.5)
        ax.axis("off")
        ax.set_title(f"{title}", fontsize=10, fontweight="bold")
        ax.text(
            4.5, 3.2, subtitle, ha="center", fontsize=7, style="italic", color="#555555"
        )

        # Time axis
        ax.plot([0.5, 8.5], [0, 0], color=GRAY3, lw=0.8)
        for t in range(1, 9):
            ax.plot([t, t], [-0.05, 0.05], color=GRAY3, lw=0.8)
            ax.text(t, -0.2, f"t{t}", ha="center", fontsize=6, color="#999999")

        # Client labels
        clients = list(dict.fromkeys([op[0] for op in operations]))
        client_y = {c: 1.0 + idx * 1.2 for idx, c in enumerate(clients)}

        for client_name, y_pos in client_y.items():
            ax.text(
                0.3,
                y_pos,
                client_name,
                ha="right",
                va="center",
                fontsize=7,
                fontweight="bold",
            )
            ax.plot([0.5, 8.5], [y_pos, y_pos], color=GRAY5, lw=0.5, linestyle=":")

        for client, t_start, t_end, label, fill in operations:
            y = client_y[client]
            rect = FancyBboxPatch(
                (t_start, y - 0.2),
                t_end - t_start,
                0.4,
                boxstyle="round,pad=0.05",
                lw=1.2,
                edgecolor=LN,
                facecolor=fill,
            )
            ax.add_patch(rect)
            ax.text(
                (t_start + t_end) / 2, y, label, ha="center", va="center", fontsize=7
            )

        # Result annotation
        ax.text(
            4.5,
            -0.45,
            result_text,
            ha="center",
            fontsize=7,
            bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY5},
        )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "linearizability_vs_sequential.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ linearizability_vs_sequential.png")


def draw_paxos_flow() -> None:
    """Draw paxos flow."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 4))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.5, 5)
    ax.axis("off")
    ax.set_title(
        "Paxos — uproszczony przebieg (zapis x=5)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Actors
    actors = [
        ("Proposer", 1.5, 4.0, GRAY1),
        ("A₁", 4.5, 4.0, GRAY2),
        ("A₂", 6.5, 4.0, GRAY2),
        ("A₃", 8.5, 4.0, GRAY2),
    ]
    for name, x, y, fill in actors:
        draw_box(
            ax, x - 0.6, y, 1.2, 0.6, name, fill=fill, fontsize=8, fontweight="bold"
        )

    # Phase 1: Prepare
    ax.text(
        -0.3,
        3.5,
        "FAZA 1\nPrepare",
        ha="center",
        fontsize=7,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    y_prep = 3.3
    for target_x in [4.5, 6.5, 8.5]:
        draw_arrow(ax, 2.1, y_prep + 0.15, target_x - 0.6, y_prep + 0.15, lw=1.0)
    ax.text(3.3, y_prep + 0.35, "Prepare(n=1)", fontsize=6, ha="center")

    # Promises back
    y_prom = 2.7
    for target_x in [4.5, 6.5]:
        draw_arrow(
            ax,
            target_x - 0.6,
            y_prom + 0.15,
            2.1,
            y_prom + 0.15,
            lw=1.0,
            color="#555555",
        )
    ax.text(
        3.3, y_prom + 0.35, "Promise(n=1) ✓", fontsize=6, ha="center", color="#555555"
    )
    ax.text(8.5, y_prom + 0.15, "(slow)", fontsize=6, ha="center", color="#999999")

    ax.text(
        1.5,
        y_prom - 0.15,
        "majority\n(2/3) ✓",
        fontsize=6,
        ha="center",
        bbox={"boxstyle": "round,pad=0.15", "facecolor": GRAY1, "edgecolor": GRAY3},
    )

    # Phase 2: Accept
    ax.text(
        -0.3,
        1.8,
        "FAZA 2\nAccept",
        ha="center",
        fontsize=7,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    y_acc = 1.6
    for target_x in [4.5, 6.5, 8.5]:
        draw_arrow(ax, 2.1, y_acc + 0.15, target_x - 0.6, y_acc + 0.15, lw=1.0)
    ax.text(3.3, y_acc + 0.35, "Accept(n=1, x=5)", fontsize=6, ha="center")

    # Accepted back
    y_accd = 1.0
    for target_x in [4.5, 6.5]:
        draw_arrow(
            ax,
            target_x - 0.6,
            y_accd + 0.15,
            2.1,
            y_accd + 0.15,
            lw=1.0,
            color="#555555",
        )
    ax.text(3.3, y_accd + 0.35, "Accepted ✓", fontsize=6, ha="center", color="#555555")

    # Result
    ax.text(
        5.0,
        0.1,
        "x=5 UZGODNIONE (majority zaakceptowała) → Linearizable!",
        fontsize=8,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY1, "edgecolor": LN},
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "paxos_flow.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ paxos_flow.png")
