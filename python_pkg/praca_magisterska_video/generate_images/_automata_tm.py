"""TM recognition diagram — TM for 0^n 1^n."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._automata_common import (
    BG,
    DPI,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY3,
    GRAY4,
    HEAD_MARKER_FONTSIZE,
    LIGHT_GREEN,
    LIGHT_YELLOW,
    LN,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


def draw_tm_recognition() -> None:
    """TM tape visualization for 0ⁿ1ⁿ with infinite tape."""
    _fig, ax = plt.subplots(1, 1, figsize=(11.69, 6.5))
    ax.set_xlim(-0.5, 13)
    ax.set_ylim(-1, 10.5)
    ax.axis("off")
    ax.set_title(
        "TM — rozpoznawanie 0ⁿ1ⁿ (n=2)\n"
        "Strategia: zaznacz jedno 0 i jedno 1"
        " w każdej rundzie",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    cell_w = 0.9
    cell_h = 0.7
    tape_x0 = 1.5
    head_color = "#FFD700"

    def draw_tape(
        tape_y: float,
        cells: list[tuple[str, str]],
        head_pos: int | None,
        label: str,
        *,
        step_label: str = "",
    ) -> None:
        """Draw tape."""
        ax.text(
            0.2,
            tape_y + cell_h / 2,
            label,
            ha="right",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )
        for i, (sym, color) in enumerate(cells):
            x = tape_x0 + i * cell_w
            fc = head_color if i == head_pos else color
            lw = 1.2
            ls = "-"
            if sym == "⊔":
                ls = "--"
            rect = mpatches.FancyBboxPatch(
                (x, tape_y),
                cell_w,
                cell_h,
                boxstyle="round,pad=0.03",
                lw=lw,
                edgecolor=LN,
                facecolor=fc,
                linestyle=ls,
            )
            ax.add_patch(rect)
            bold = "bold" if sym in ("X", "Y") else "normal"
            clr = GRAY3 if sym == "⊔" else LN
            ax.text(
                x + cell_w / 2,
                tape_y + cell_h / 2,
                sym,
                ha="center",
                va="center",
                fontsize=FS + 2,
                fontweight=bold,
                family="monospace",
                color=clr,
            )
        # ∞ arrow
        last_x = tape_x0 + len(cells) * cell_w
        ax.annotate(
            "→ ∞",
            xy=(last_x + 0.3, tape_y + cell_h / 2),
            fontsize=FS,
            ha="left",
            va="center",
            color=GRAY3,
        )
        if head_pos is not None:
            hx = tape_x0 + head_pos * cell_w + cell_w / 2
            ax.annotate(
                "▼",
                xy=(hx, tape_y + cell_h),
                xytext=(hx, tape_y + cell_h + 0.25),
                ha="center",
                va="bottom",
                fontsize=HEAD_MARKER_FONTSIZE,
                color="black",
            )
        if step_label:  # pragma: no branch
            sx = tape_x0 + 8 * cell_w + 0.8
            ax.text(
                sx,
                tape_y + cell_h / 2,
                step_label,
                ha="left",
                va="center",
                fontsize=FS_SMALL,
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "facecolor": GRAY4,
                    "edgecolor": GRAY3,
                },
            )

    white = "white"
    mk = GRAY1
    bl = "#F0F0F0"  # blank cell

    tape_rows = [
        (
            9.0,
            [
                ("0", white),
                ("0", white),
                ("1", white),
                ("1", white),
                ("⊔", bl),
                ("⊔", bl),
                ("⊔", bl),
            ],
            0,
            "Początek",
            "taśma = [0,0,1,1,⊔,⊔,...∞]",
        ),
        (
            7.8,
            [
                ("X", mk),
                ("0", white),
                ("1", white),
                ("1", white),
                ("⊔", bl),
                ("⊔", bl),
                ("⊔", bl),
            ],
            1,
            "R1, krok 1",
            "zaznacz 0→X, idź w prawo",
        ),
        (
            6.6,
            [
                ("X", mk),
                ("0", white),
                ("Y", mk),
                ("1", white),
                ("⊔", bl),
                ("⊔", bl),
                ("⊔", bl),
            ],
            0,
            "R1, krok 2",
            "zaznacz 1→Y, wróć na początek",
        ),
        (
            4.8,
            [
                ("X", mk),
                ("X", mk),
                ("Y", mk),
                ("1", white),
                ("⊔", bl),
                ("⊔", bl),
                ("⊔", bl),
            ],
            2,
            "R2, krok 1",
            "pomiń X, zaznacz 0→X",
        ),
        (
            3.6,
            [
                ("X", mk),
                ("X", mk),
                ("Y", mk),
                ("Y", mk),
                ("⊔", bl),
                ("⊔", bl),
                ("⊔", bl),
            ],
            0,
            "R2, krok 2",
            "pomiń Y, zaznacz 1→Y, wróć",
        ),
        (
            2.4,
            [
                ("X", mk),
                ("X", mk),
                ("Y", mk),
                ("Y", mk),
                ("⊔", bl),
                ("⊔", bl),
                ("⊔", bl),
            ],
            None,
            "Sprawdzenie",
            "brak niezaznaczonych → q_acc",
        ),
    ]

    # Runda 2 header
    runda2_y = 5.8
    ax.text(
        tape_x0 + 3.5 * cell_w,
        runda2_y + 0.3,
        "═══ RUNDA 2 ═══",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
    )

    for row_y, cells, head, lbl, step in tape_rows:
        draw_tape(row_y, cells, head, lbl, step_label=step)

    # Result + TM vs LBA comparison
    tape_y = 0.8
    ax.text(
        tape_x0 + 3.5 * cell_w,
        tape_y + 0.3,
        '"0011" AKCEPTOWANE ✓',
        ha="center",
        va="center",
        fontsize=FS + 1,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_GREEN,
            "edgecolor": LN,
        },
    )

    tape_y = -0.3
    ax.text(
        tape_x0 + 3.5 * cell_w,
        tape_y + 0.3,
        "Różnica TM vs LBA: taśma TM jest "
        "nieskończona (⊔ → ∞)\n"
        "LBA: głowica ograniczona do |w| komórek\n"
        "TM: głowica może wyjść POZA wejście "
        "i pisać na pustych ⊔",
        ha="center",
        va="center",
        fontsize=FS_SMALL,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": LIGHT_YELLOW,
            "edgecolor": GRAY3,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "tm_recognition_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    logger.info("  ✓ tm_recognition_example.png")
