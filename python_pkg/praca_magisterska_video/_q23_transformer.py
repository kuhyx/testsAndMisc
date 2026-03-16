"""Transformer segmentation and methods comparison for Q23 video."""

from __future__ import annotations

from moviepy import (
    ColorClip,
    CompositeVideoClip,
    VideoClip,
)
from moviepy.video.fx import FadeIn, FadeOut
import numpy as np

from python_pkg.praca_magisterska_video._q23_helpers import (
    BG_COLOR,
    FONT_B,
    FONT_R,
    FPS,
    STEP_DUR,
    H,
    W,
    _compose_slide,
    _tc,
    _text_slide,
)


# ── Transformer Segmentation ────────────────────────────────────
def _draw_base_grid(
    frame: np.ndarray,
    gx: int,
    gy: int,
    grid_n: int,
    cell: int,
) -> None:
    """Draw an empty grid of cells."""
    for r in range(grid_n):
        for c in range(grid_n):
            x = gx + c * cell
            y = gy + r * cell
            frame[y : y + cell - 2, x : x + cell - 2] = (35, 40, 55)


def _draw_cnn_kernel(
    frame: np.ndarray,
    lx: int,
    ly: int,
    cell: int,
    progress: float,
) -> None:
    """Highlight a 3x3 CNN kernel on the grid."""
    cnn_phase = 0.2
    if progress <= cnn_phase:
        return
    cx, cy = 2, 2
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            r, c = cy + dr, cx + dc
            x = lx + c * cell
            y = ly + r * cell
            frame[y : y + cell - 2, x : x + cell - 2] = (70, 130, 200)
    x = lx + cx * cell
    y = ly + cy * cell
    frame[y : y + cell - 2, x : x + cell - 2] = (120, 180, 255)


def _draw_conn_line(
    frame: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> None:
    """Draw a dashed connection line between two points."""
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps <= 0:
        return
    for s in range(0, steps, 3):
        px = x0 + int((x1 - x0) * s / steps)
        py = y0 + int((y1 - y0) * s / steps)
        if 0 <= px < W - 1 and 0 <= py < H - 1:
            frame[py : py + 1, px : px + 1] = (200, 180, 50)


def _draw_attention_connections(
    frame: np.ndarray,
    origin: tuple[int, int],
    grid_n: int,
    cell: int,
    progress: float,
) -> None:
    """Draw transformer self-attention connections on the grid."""
    rx, ry = origin
    transformer_phase = 0.4
    if progress <= transformer_phase:
        return
    cx_t, cy_t = 2, 2
    x0 = rx + cx_t * cell + cell // 2
    y0 = ry + cy_t * cell + cell // 2
    n_connections = int(progress * 36)
    conn_idx = 0
    for r in range(grid_n):
        for c in range(grid_n):
            conn_idx += 1
            if conn_idx > n_connections:
                break
            x = rx + c * cell
            y = ry + r * cell
            dist = abs(r - cy_t) + abs(c - cx_t)
            strength = max(30, 200 - dist * 30)
            frame[y : y + cell - 2, x : x + cell - 2] = (
                strength // 3,
                strength // 2,
                strength,
            )
            _draw_conn_line(frame, x0, y0, x + cell // 2, y + cell // 2)
        else:
            continue
        break
    x = rx + cx_t * cell
    y = ry + cy_t * cell
    frame[y : y + cell - 2, x : x + cell - 2] = (255, 200, 50)


def _make_attention_frame(t: float) -> np.ndarray:
    """Render a CNN-vs-Transformer attention comparison frame."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = BG_COLOR
    progress = min(t / (STEP_DUR * 0.7), 1.0)

    cell = 40
    grid_n = 6

    lx, ly = 60, 200
    _draw_base_grid(frame, lx, ly, grid_n, cell)
    _draw_cnn_kernel(frame, lx, ly, cell, progress)

    rx, ry = 680, 200
    _draw_base_grid(frame, rx, ry, grid_n, cell)
    _draw_attention_connections(frame, (rx, ry), grid_n, cell, progress)

    return frame


def _transformer_seg_demo() -> list[CompositeVideoClip]:
    """Animate transformer-based segmentation: self-attention concept."""
    dur = STEP_DUR + 1

    # Slide 1: CNN local vs Transformer global
    att_clip = VideoClip(_make_attention_frame, duration=dur).with_fps(FPS)
    labels = [
        ("Transformer: Self-Attention w segmentacji", 26, "#FFE082", FONT_B, (80, 20)),
        ("CNN = LOKALNY kontekst", 18, "#64B5F6", FONT_B, (60, 160)),
        ("Transformer = GLOBALNY kontekst", 18, "#FFE082", FONT_B, (680, 160)),
        ("Filtr 3x3 widzi", 14, "#64B5F6", FONT_R, (60, 460)),
        ("TYLKO 9 sąsiadów", 14, "#64B5F6", FONT_R, (60, 485)),
        ("Self-attention: każdy", 14, "#FFE082", FONT_R, (680, 460)),
        ("piksel widzi WSZYSTKIE!", 14, "#FFE082", FONT_R, (680, 485)),
        ("vs", 28, "#B0BEC5", FONT_B, (450, 300)),
    ]
    slides = [_compose_slide(att_clip, labels, dur)]

    # Slide 2: Self-attention Q/K/V step by step
    qkv_lines = [
        ("Self-Attention: Q / K / V krok po kroku", 26, "#FFE082", FONT_B, (80, 30)),
        ("Każdy piksel (token) tworzy 3 wektory:", 18, "#B0BEC5", FONT_R, (100, 100)),
        (
            "  Q (Query)  = 'czego szukam?' - pytanie piksela",
            17,
            "#64B5F6",
            FONT_R,
            (120, 145),
        ),
        (
            "  K (Key)    = 'co oferuj\u0119?' - odpowied\u017a piksela",
            17,
            "#A5D6A7",
            FONT_R,
            (120, 185),
        ),
        (
            "  V (Value)  = 'moja warto\u015b\u0107' - informacja do przekazania",
            17,
            "#FFE082",
            FONT_R,
            (120, 225),
        ),
        ("Algorytm attention:", 18, "#B0BEC5", FONT_R, (100, 285)),
        (
            "  1. Mnożenie Q x K\u1d40 → macierz NxN (kto ważny dla kogo)",
            16,
            "white",
            FONT_R,
            (120, 320),
        ),
        (
            "  2. Skalowanie: / \u221ad (stabilno\u015b\u0107 gradient\u00f3w)",
            16,
            "white",
            FONT_R,
            (120, 355),
        ),
        (
            "  3. Softmax \u2192 wagi attention (sumuj\u0105 si\u0119 do 1)",
            16,
            "white",
            FONT_R,
            (120, 390),
        ),
        (
            "  4. Mno\u017cenie wag x V \u2192 wa\u017cona suma warto\u015bci",
            16,
            "white",
            FONT_R,
            (120, 425),
        ),
        (
            "Attention(Q,K,V) = softmax(Q \u00b7 K\u1d40 / \u221ad) \u00b7 V",
            20,
            "#FFE082",
            FONT_B,
            (100, 480),
        ),
        (
            "Z\u0142o\u017cono\u015b\u0107: O(n\u00b2) pami\u0119ci \u2014 n = liczba pikseli/token\u00f3w",
            16,
            "#EF9A9A",
            FONT_R,
            (100, 535),
        ),
        (
            "Dlatego SegFormer u\u017cywa efficient attention (liniowa z\u0142o\u017cono\u015b\u0107)",
            15,
            "#78909C",
            FONT_R,
            (100, 570),
        ),
        (
            "SegFormer (2021): lightweight + hierarchiczny encoder",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 610),
        ),
        (
            "Mask2Former (2022): masked attention + "
            "unified (semantic+instance+panoptic)",
            16,
            "#CE93D8",
            FONT_R,
            (100, 645),
        ),
    ]
    slides.append(_text_slide(qkv_lines, duration=STEP_DUR + 1))

    # Slide 3: Encoder-Decoder in DL summary
    summary_lines = [
        (
            "Podsumowanie: Encoder-Decoder w segmentacji DL",
            24,
            "#FFE082",
            FONT_B,
            (80, 30),
        ),
        (
            "Wsp\u00f3lna idea WSZYSTKICH sieci segmentacji:",
            18,
            "#B0BEC5",
            FONT_R,
            (80, 90),
        ),
        (
            "Encoder:  obraz \u2192 cechy (zmniejsza rozdzielczo\u015b\u0107, wyci\u0105ga CO)",
            16,
            "#64B5F6",
            FONT_R,
            (100, 140),
        ),
        (
            "Decoder:  cechy \u2192 mapa (zwi\u0119ksza rozdzielczo\u015b\u0107, odtwarza GDZIE)",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 175),
        ),
        (
            "Skip:     przenosi detale z encodera do decodera",
            16,
            "#FFE082",
            FONT_R,
            (100, 210),
        ),
        ("", 10, "white", FONT_R, (100, 240)),
        (
            "FCN (2015):     Conv1x1 + skip \u2192 pierwsza end-to-end",
            16,
            "#64B5F6",
            FONT_R,
            (100, 275),
        ),
        (
            "U-Net (2015):   U-shape + skip concat \u2192 segmentacja medyczna",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 310),
        ),
        (
            "DeepLab (2018): dilated conv + ASPP \u2192 multi-scale kontekst",
            16,
            "#FFE082",
            FONT_R,
            (100, 345),
        ),
        (
            "SegFormer:      transformer encoder (globalny kontekst)",
            16,
            "#CE93D8",
            FONT_R,
            (100, 380),
        ),
        (
            "Mask2Former:    masked attention (unified, SOTA)",
            16,
            "#CE93D8",
            FONT_R,
            (100, 415),
        ),
        ("", 10, "white", FONT_R, (100, 440)),
        (
            "Ewolucja: wi\u0119cej kontekstu + lepsze skip connections:",
            17,
            "white",
            FONT_R,
            (80, 465),
        ),
        (
            "  CNN lokal. \u2192 dilated (szersze RF) \u2192 transformer (global) \u2192 masked att.",
            16,
            "#B0BEC5",
            FONT_R,
            (80, 505),
        ),
        (
            "  addition skip \u2192 concat skip \u2192 cross-attention skip",
            16,
            "#B0BEC5",
            FONT_R,
            (80, 540),
        ),
        (
            "Metryki: mIoU (standard), Dice (medycyna), Focal Loss (imbalance)",
            16,
            "#90CAF9",
            FONT_R,
            (80, 590),
        ),
        (
            "Loss: Cross-Entropy per piksel + opcjonalnie Dice/Focal",
            15,
            "#78909C",
            FONT_R,
            (80, 625),
        ),
    ]
    slides.append(_text_slide(summary_lines, duration=STEP_DUR + 1))

    return slides


# ── Methods comparison ────────────────────────────────────────────
def _methods_comparison() -> CompositeVideoClip:
    """Create a comparison table of all segmentation methods."""
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(10.0)
    title = (
        _tc(
            text="Por\u00f3wnanie metod segmentacji",
            font_size=36,
            color="white",
            font=FONT_B,
        )
        .with_duration(10.0)
        .with_position(("center", 20))
    )

    rows = [
        ("Metoda", "Typ", "Idea", "Mnemonik"),
        (
            "Thresholding",
            "Klasyczna",
            "piksel > T \u2192 klasa 1",
            "PR\u00d3G na bramce",
        ),
        ("Otsu", "Klasyczna", "auto-pr\u00f3g, min \u03c3\u00b2", "AUTO-bramkarz"),
        ("Region Growing", "Klasyczna", "BFS od seeda", "PLAMA atramentu"),
        ("Watershed", "Klasyczna", "zalewanie minim\u00f3w", "ZALEWANIE terenu"),
        (
            "Mean Shift",
            "Klasyczna",
            "j\u0105dro \u2192 max g\u0119sto\u015bci",
            "KULKI do do\u0142k\u00f3w",
        ),
        ("U-Net", "Deep Learning", "encoder-decoder + skip", "Litera U + mosty"),
        ("DeepLab", "Deep Learning", "dilated conv + ASPP", "DZIURY w filtrze"),
    ]

    clips: list[VideoClip] = [bg, title]
    mnemonic_col = 3
    for i, row in enumerate(rows):
        y_pos = 75 + i * 72
        col_x = [40, 210, 340, 660]
        for j, cell in enumerate(row):
            fs = 16 if i > 0 else 18
            color = (
                "#64B5F6" if i == 0 else ("#E0E0E0" if j < mnemonic_col else "#FFE082")
            )
            tc = (
                _tc(
                    text=cell,
                    font_size=fs,
                    color=color,
                    font=FONT_B if i == 0 else FONT_R,
                )
                .with_duration(10.0)
                .with_position((col_x[j], y_pos))
            )
            clips.append(tc)

    return CompositeVideoClip(clips, size=(W, H)).with_effects(
        [FadeIn(0.5), FadeOut(0.5)]
    )
