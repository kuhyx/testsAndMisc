"""LBA recognition diagram — LBA for a^n b^n c^n."""

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


def draw_lba_recognition() -> None:
    """LBA tape visualization showing marking rounds for 'aabbcc'."""
    _fig, ax = plt.subplots(1, 1, figsize=(11.69, 6.5))
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-1, 10.5)
    ax.axis("off")
    ax.set_title(
        "LBA — rozpoznawanie aⁿbⁿcⁿ (n=2)\n"
        "Strategia: w każdej rundzie zaznacz jedno a, b, c",
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
        """Draw a tape row with cells, head highlighted."""
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
            rect = mpatches.FancyBboxPatch(
                (x, tape_y),
                cell_w,
                cell_h,
                boxstyle="round,pad=0.03",
                lw=1.2,
                edgecolor=LN,
                facecolor=fc,
            )
            ax.add_patch(rect)
            bold = "bold" if sym in ("X", "Y", "Z") else "normal"
            ax.text(
                x + cell_w / 2,
                tape_y + cell_h / 2,
                sym,
                ha="center",
                va="center",
                fontsize=FS + 2,
                fontweight=bold,
                family="monospace",
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
        if step_label:
            sx = tape_x0 + 6 * cell_w + 0.5
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
    mk = GRAY1  # marked cell color

    # Row 1: Initial tape
    tape_y = 9.0
    draw_tape(
        tape_y,
        [
            ("a", white),
            ("a", white),
            ("b", white),
            ("b", white),
            ("c", white),
            ("c", white),
        ],
        0,
        "Początek",
        step_label=("taśma = [a, a, b, b, c, c], głowica na 0"),
    )

    # Row 2: After marking first 'a'
    tape_y = 7.8
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("a", white),
            ("b", white),
            ("b", white),
            ("c", white),
            ("c", white),
        ],
        1,
        "R1, krok 1",
        step_label="zaznacz a→X, szukaj b",
    )

    # Row 3: After marking first 'b'
    tape_y = 6.6
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("a", white),
            ("Y", mk),
            ("b", white),
            ("c", white),
            ("c", white),
        ],
        3,
        "R1, krok 2",
        step_label="zaznacz b→Y, szukaj c",
    )

    # Row 4: After marking first 'c'
    tape_y = 5.4
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("a", white),
            ("Y", mk),
            ("b", white),
            ("Z", mk),
            ("c", white),
        ],
        0,
        "R1, krok 3",
        step_label="zaznacz c→Z, wróć na początek",
    )

    # Runda 2 header
    tape_y = 4.5
    ax.text(
        tape_x0 + 3 * cell_w,
        tape_y + 0.3,
        "═══ RUNDA 2 ═══",
        ha="center",
        va="center",
        fontsize=FS,
        fontweight="bold",
        color=LN,
    )

    # Row 5: After marking second 'a'
    tape_y = 3.6
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("X", mk),
            ("Y", mk),
            ("b", white),
            ("Z", mk),
            ("c", white),
        ],
        2,
        "R2, krok 1",
        step_label="pomiń X, zaznacz a→X, szukaj b",
    )

    # Row 6: After marking second 'b'
    tape_y = 2.4
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("X", mk),
            ("Y", mk),
            ("Y", mk),
            ("Z", mk),
            ("c", white),
        ],
        4,
        "R2, krok 2",
        step_label="pomiń Y, zaznacz b→Y, szukaj c",
    )

    # Row 7: After marking second 'c'
    tape_y = 1.2
    draw_tape(
        tape_y,
        [
            ("X", mk),
            ("X", mk),
            ("Y", mk),
            ("Y", mk),
            ("Z", mk),
            ("Z", mk),
        ],
        None,
        "R2, krok 3",
        step_label="zaznacz c→Z, wróć na początek",
    )

    # Result
    tape_y = 0.0
    ax.text(
        tape_x0 + 3 * cell_w,
        tape_y + 0.3,
        "Wszystko zaznaczone → q_acc" ' → "aabbcc" AKCEPTOWANE ✓',
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

    # Key
    ax.text(
        tape_x0 + 6 * cell_w + 0.5,
        tape_y + 0.3,
        "Ograniczenie LBA:\n" "głowica ≤ 6 komórek\n" '(= |w| = |"aabbcc"|)',
        ha="left",
        va="center",
        fontsize=FS_SMALL,
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_YELLOW,
            "edgecolor": GRAY3,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "lba_recognition_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    logger.info("  ✓ lba_recognition_example.png")
