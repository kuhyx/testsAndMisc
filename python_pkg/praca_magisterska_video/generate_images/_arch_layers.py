"""Zachman Framework and ArchiMate layer diagram generation."""

from __future__ import annotations

import logging
from pathlib import Path

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
    draw_arrow,
    draw_box,
)

_logger = logging.getLogger(__name__)


# =========================================================================
# 4. Zachman Framework Grid
# =========================================================================
def generate_zachman() -> None:
    """Generate zachman."""
    fig, ax = plt.subplots(figsize=(8.27, 6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 65)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "Zachman Framework \u2014 taksonomia architektury",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    rows = [
        "Kontekst\n(Planner)",
        "Konceptualny\n(Owner)",
        "Logiczny\n(Designer)",
        "Fizyczny\n(Builder)",
        "Szczeg\u00f3\u0142owy\n(Subcontractor)",
    ]
    cols = [
        "Co?\n(dane)",
        "Jak?\n(funkcje)",
        "Gdzie?\n(sie\u0107)",
        "Kto?\n(ludzie)",
        "Kiedy?\n(czas)",
        "Dlaczego?\n(cel)",
    ]

    n_rows = len(rows)
    n_cols = len(cols)

    x0 = 18
    y0 = 5
    cw = 12.5  # cell width
    ch = 9  # cell height
    rh_label = 14  # row label width

    # Column headers
    for j, col in enumerate(cols):
        x = x0 + j * cw
        draw_box(
            ax,
            x,
            y0 + n_rows * ch,
            cw,
            7,
            col,
            fill=GRAY2,
            lw=1.5,
            fontsize=6.5,
            fontweight="bold",
        )

    # Row headers
    for i, row in enumerate(rows):
        y = y0 + (n_rows - 1 - i) * ch
        draw_box(
            ax,
            x0 - rh_label,
            y,
            rh_label,
            ch,
            row,
            fill=GRAY2,
            lw=1.5,
            fontsize=6.5,
            fontweight="bold",
        )

    # Cells
    fills = [GRAY4, "white"]
    for i in range(n_rows):
        for j in range(n_cols):
            x = x0 + j * cw
            y = y0 + (n_rows - 1 - i) * ch
            fill = fills[(i + j) % 2]
            ax.add_patch(
                plt.Rectangle((x, y), cw, ch, lw=0.8, edgecolor=LN, facecolor=fill)
            )

    # Sample content in a few cells
    examples = {
        (0, 0): "Lista\nencji",
        (0, 1): "Lista\nproces\u00f3w",
        (0, 2): "Lokalizacje",
        (1, 0): "Model\npoj\u0119ciowy",
        (1, 1): "Model\nproces\u00f3w",
        (2, 0): "ERD",
        (2, 1): "Data Flow",
        (3, 0): "Schemat\nDB",
        (3, 1): "Kod\nprogramu",
        (0, 3): "Role",
        (1, 3): "Org chart",
        (0, 4): "Harmonogram",
        (0, 5): "Cele\nbiznesowe",
    }
    for (i, j), text in examples.items():
        x = x0 + j * cw
        y = y0 + (n_rows - 1 - i) * ch
        ax.text(
            x + cw / 2,
            y + ch / 2,
            text,
            ha="center",
            va="center",
            fontsize=5.5,
            fontstyle="italic",
            color="#444444",
        )

    # Note
    ax.text(
        50,
        1,
        "Każda komórka = artefakt opisujący system"
        " z danej perspektywy i aspektu.\n"
        "Zachman nie mówi JAK modelować"
        " — mówi CO należy udokumentować.",
        ha="center",
        fontsize=7,
        fontstyle="italic",
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "zachman_framework.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK Zachman Framework")


# =========================================================================
# 5. ArchiMate Layers
# =========================================================================
def generate_archimate() -> None:
    """Generate archimate."""
    fig, ax = plt.subplots(figsize=(8.27, 9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "ArchiMate \u2014 3 warstwy \u00d7 3 aspekty",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    # Column headers (aspects)
    headers = [
        ("Active Structure\n(KTO?)", 0),
        ("Behavior\n(CO robi?)", 1),
        ("Passive Structure\n(NA CZYM?)", 2),
    ]

    x0 = 10
    y0 = 10
    cw = 26
    ch = 20
    gap = 1
    header_h = 8
    row_label_w = 14

    # Column headers
    for label, j in headers:
        x = x0 + row_label_w + j * (cw + gap)
        draw_box(
            ax,
            x,
            y0 + 3 * (ch + gap),
            cw,
            header_h,
            label,
            fill=GRAY3,
            lw=1.5,
            fontsize=8,
            fontweight="bold",
        )

    # Layer rows
    layers = [
        (
            "Business\nLayer",
            GRAY1,
            [
                ("Business\nActor", "Business\nProcess", "Business\nObject"),
                ("(Kto wykonuje?)", "(Co si\u0119 dzieje?)", "(Na czym dzia\u0142a?)"),
                (
                    "np. Klient,\nHandlowiec",
                    "np. Obs\u0142uga\nzam\u00f3wienia",
                    "np. Zam\u00f3wienie,\nFaktura",
                ),
            ],
        ),
        (
            "Application\nLayer",
            GRAY4,
            [
                ("Application\nComponent", "Application\nService", "Data\nObject"),
                ("(Jaki modu\u0142?)", "(Jaka us\u0142uga?)", "(Jakie dane?)"),
                ("np. CRM,\nERP", "np. API\nzam\u00f3wie\u0144", "np. tabela\nOrders"),
            ],
        ),
        (
            "Technology\nLayer",
            "white",
            [
                ("Node /\nDevice", "Infrastructure\nService", "Artifact"),
                ("(Jaki sprz\u0119t?)", "(Jaka infra?)", "(Jaki plik?)"),
                (
                    "np. Serwer\nLinux, K8s",
                    "np. Load\nBalancer",
                    "np. .jar,\n.war, image",
                ),
            ],
        ),
    ]

    for i, (layer_name, fill, cells) in enumerate(layers):
        y = y0 + (2 - i) * (ch + gap)

        # Row label
        draw_box(
            ax,
            x0,
            y,
            row_label_w,
            ch,
            layer_name,
            fill=GRAY2,
            lw=1.5,
            fontsize=8,
            fontweight="bold",
        )

        for j in range(3):
            x = x0 + row_label_w + j * (cw + gap)
            ax.add_patch(
                plt.Rectangle((x, y), cw, ch, lw=1.5, edgecolor=LN, facecolor=fill)
            )
            # Element name (bold)
            ax.text(
                x + cw / 2,
                y + ch - 3,
                cells[0][j],
                ha="center",
                va="top",
                fontsize=7,
                fontweight="bold",
            )
            # Role description
            ax.text(
                x + cw / 2,
                y + ch / 2,
                cells[1][j],
                ha="center",
                va="center",
                fontsize=6,
                fontstyle="italic",
                color="#555555",
            )
            # Example
            ax.text(
                x + cw / 2,
                y + 3,
                cells[2][j],
                ha="center",
                va="bottom",
                fontsize=6,
                color="#333333",
            )

    # Vertical arrows between layers
    for j in range(3):
        x = x0 + row_label_w + j * (cw + gap) + cw / 2
        for i in range(2):
            y_top = y0 + (2 - i) * (ch + gap)
            y_bot = y0 + (2 - i - 1) * (ch + gap) + ch
            draw_arrow(ax, x, y_top, x, y_bot + 0.3, lw=1)

    # Arrow labels
    mid_x = x0 + row_label_w - 3
    ax.text(
        mid_x,
        y0 + 2 * (ch + gap) - gap / 2,
        "realizacja \u2193",
        fontsize=6,
        ha="right",
        va="center",
        fontstyle="italic",
        rotation=90,
    )
    ax.text(
        mid_x,
        y0 + 1 * (ch + gap) - gap / 2,
        "realizacja \u2193",
        fontsize=6,
        ha="right",
        va="center",
        fontstyle="italic",
        rotation=90,
    )

    # Note
    ax.text(
        50,
        4,
        "Warstwy czytamy z g\u00f3ry (biznes) na d\u00f3\u0142 (technologia).\n"
        "Ni\u017csze warstwy REALIZUJ\u0104 wy\u017csze. "
        "ArchiMate jest komplementarny z TOGAF.",
        ha="center",
        fontsize=7,
        fontstyle="italic",
    )

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "archimate_layers.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK ArchiMate")
