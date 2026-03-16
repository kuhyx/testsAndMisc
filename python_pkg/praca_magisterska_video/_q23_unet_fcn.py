"""U-Net and FCN architecture animations for Q23 segmentation video."""

from __future__ import annotations

from moviepy import (
    CompositeVideoClip,
    VideoClip,
)
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
    _text_slide,
)


# ── U-Net Architecture ───────────────────────────────────────────
def _draw_unet_skips(
    frame: np.ndarray,
    enc_positions: list[tuple[int, int, int, int]],
    n_blocks: int,
    dec_x: int,
    skip_threshold: int,
) -> None:
    """Draw horizontal dashed skip-connection lines."""
    if n_blocks <= skip_threshold:
        return
    for i in range(min(n_blocks - 5, 4)):
        ey = enc_positions[i][1] + enc_positions[i][3] // 2
        ex_end = enc_positions[i][0] + enc_positions[i][2]
        for dash_x in range(ex_end + 10, dec_x - 10, 15):
            frame[ey : ey + 2, dash_x : dash_x + 8] = (255, 200, 50)


def _make_unet_frame(t: float) -> np.ndarray:
    """Render a single U-Net animation frame."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = BG_COLOR

    enc_sizes = [(80, 120), (60, 100), (45, 80), (30, 60)]
    dec_sizes = list(reversed(enc_sizes))
    enc_x = 150
    dec_x = 850

    progress = min(t / (STEP_DUR * 0.6), 1.0)
    n_blocks = int(progress * 8) + 1

    enc_positions: list[tuple[int, int, int, int]] = []
    y_offset = 120
    for i, (bw, bh) in enumerate(enc_sizes):
        x = enc_x
        y = y_offset + i * 130
        enc_positions.append((x, y, bw, bh))
        if i < n_blocks:
            frame[y : y + bh, x : x + bw] = (70, 130, 200)
            frame[y : y + 2, x : x + bw] = (100, 180, 255)
            frame[y + bh - 2 : y + bh, x : x + bw] = (100, 180, 255)
            frame[y : y + bh, x : x + 2] = (100, 180, 255)
            frame[y : y + bh, x + bw - 2 : x + bw] = (100, 180, 255)
            if i < len(enc_sizes) - 1:
                ax = x + bw // 2
                ay = y + bh + 10
                frame[ay : ay + 20, ax - 1 : ax + 2] = (150, 150, 170)

    bx, by = 500, y_offset + 3 * 130 + 30
    encoder_count = 4
    if n_blocks > encoder_count:
        frame[by : by + 50, bx : bx + 25] = (200, 100, 80)
        frame[by : by + 2, bx : bx + 25] = (255, 140, 100)
        frame[by + 48 : by + 50, bx : bx + 25] = (255, 140, 100)

    for i, (bw, bh) in enumerate(dec_sizes):
        x = dec_x
        y = y_offset + (3 - i) * 130
        if n_blocks > 4 + i + 1:
            frame[y : y + bh, x : x + bw] = (80, 200, 120)
            frame[y : y + 2, x : x + bw] = (120, 230, 150)
            frame[y + bh - 2 : y + bh, x : x + bw] = (120, 230, 150)
            frame[y : y + bh, x : x + 2] = (120, 230, 150)
            frame[y : y + bh, x + bw - 2 : x + bw] = (120, 230, 150)
            if i < len(dec_sizes) - 1:
                ax = x + bw // 2
                ay = y - 30
                frame[ay : ay + 20, ax - 1 : ax + 2] = (150, 150, 170)

    skip_threshold = 5
    _draw_unet_skips(frame, enc_positions, n_blocks, dec_x, skip_threshold)

    return frame


def _unet_demo() -> list[CompositeVideoClip]:
    """Animate U-Net encoder-decoder architecture."""
    dur = STEP_DUR + 1
    unet_clip = VideoClip(_make_unet_frame, duration=dur).with_fps(FPS)
    labels = [
        ("U-Net: Encoder-Decoder + Skip Connections", 28, "#FFE082", FONT_B, (80, 20)),
        (
            "Niebieski = Encoder (↓ zmniejsza rozdzielczość, wyciąga cechy)",
            16,
            "#64B5F6",
            FONT_R,
            (80, 65),
        ),
        (
            "Zielony = Decoder (↑ zwiększa rozdzielczość, odtwarza mapę)",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 90),
        ),
        (
            "Żółte przerywane = Skip connections (przenoszą detale z encodera)",
            16,
            "#FFE082",
            FONT_R,
            (80, 115),
        ),
        (
            "Czerwony = Bottleneck (najgłębsza warstwa, max abstrakcja)",
            16,
            "#EF9A9A",
            FONT_R,
            (450, 570),
        ),
        (
            "Kształt U: encoder ↓ decoder ↑, mosty pośrodku",
            18,
            "white",
            FONT_R,
            (80, 640),
        ),
        (
            "Concatenation: skip łączy kanały (więcej informacji niż dodawanie)",
            16,
            "#78909C",
            FONT_R,
            (80, 670),
        ),
    ]
    return [_compose_slide(unet_clip, labels, dur)]


# ── FCN Architecture ─────────────────────────────────────────────
def _draw_pipeline_blocks(
    frame: np.ndarray,
    blocks: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int, int]]],
    n_visible: int,
    arrow_limit: int,
) -> None:
    """Draw coloured blocks with connecting arrows."""
    for i, ((bx, by), (bw, bh), color) in enumerate(blocks):
        if i < n_visible:
            frame[by : by + bh, bx : bx + bw] = color
            frame[by : by + 2, bx : bx + bw] = tuple(min(c + 50, 255) for c in color)
            frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                min(c + 50, 255) for c in color
            )
            if i < arrow_limit:
                ax = bx + bw + 3
                ay = by + bh // 2
                frame[ay - 1 : ay + 2, ax : ax + 12] = (150, 150, 170)


def _draw_red_cross(
    frame: np.ndarray,
    x_start: int,
    width: int,
    top_y: int,
    height: int,
) -> None:
    """Draw a red X across the given rectangle."""
    for d in range(-2, 3):
        for step in range(height):
            x1 = x_start + int(step * width / height)
            y1 = top_y + step + d
            if 0 <= y1 < H and 0 <= x1 < W:
                frame[y1, x1] = (255, 80, 80)
            y2 = top_y + height - step + d
            if 0 <= y2 < H and 0 <= x1 < W:
                frame[y2, x1] = (255, 80, 80)


def _make_fcn_frame(t: float) -> np.ndarray:
    """Render a single FCN comparison frame."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = BG_COLOR
    progress = min(t / (STEP_DUR * 0.8), 1.0)

    top_y = 140
    blocks_classic = [
        ((80, top_y), (70, 50), (70, 130, 200)),
        ((170, top_y), (50, 40), (50, 100, 160)),
        ((240, top_y), (60, 50), (70, 130, 200)),
        ((320, top_y), (40, 35), (50, 100, 160)),
        ((385, top_y), (55, 50), (160, 80, 60)),
        ((465, top_y), (55, 50), (180, 60, 60)),
        ((545, top_y), (80, 50), (200, 80, 80)),
    ]
    n_top = min(int(progress * 7) + 1, 7)
    arrow_limit = 6
    _draw_pipeline_blocks(frame, blocks_classic, n_top, arrow_limit)

    cross_phase = 0.6
    if progress > cross_phase:
        _draw_red_cross(frame, 385, 135, top_y, 50)

    bot_y = 380
    blocks_fcn = [
        ((80, bot_y), (70, 50), (70, 130, 200)),
        ((170, bot_y), (50, 40), (50, 100, 160)),
        ((240, bot_y), (60, 50), (70, 130, 200)),
        ((320, bot_y), (40, 35), (50, 100, 160)),
        ((385, bot_y), (70, 50), (80, 200, 120)),
        ((480, bot_y), (75, 50), (200, 160, 80)),
        ((580, bot_y), (80, 50), (100, 200, 100)),
    ]
    fcn_phase = 0.4
    if progress > fcn_phase:
        n_bot = min(int((progress - fcn_phase) / 0.6 * 7) + 1, 7)
        _draw_pipeline_blocks(frame, blocks_fcn, n_bot, arrow_limit)

    return frame


def _fcn_demo() -> list[CompositeVideoClip]:
    """Animate FCN step-by-step: FC → Conv 1x1 transformation."""
    dur = STEP_DUR + 1
    fcn_clip = VideoClip(_make_fcn_frame, duration=dur).with_fps(FPS)
    labels = [
        ("FCN: Fully Convolutional Network (2015)", 26, "#FFE082", FONT_B, (80, 20)),
        ("KROK 1: Zamień FC → Conv 1x1", 18, "#A5D6A7", FONT_R, (80, 60)),
        ("Klasyczny CNN:", 16, "#EF9A9A", FONT_B, (80, 105)),
        ("Conv", 11, "white", FONT_R, (92, 148)),
        ("Pool", 11, "white", FONT_R, (178, 148)),
        ("Conv", 11, "white", FONT_R, (250, 148)),
        ("Pool", 11, "white", FONT_R, (325, 148)),
        ("Flatten", 11, "#EF9A9A", FONT_R, (390, 148)),
        ("FC", 11, "#EF9A9A", FONT_R, (480, 148)),
        ("1 label", 11, "#EF9A9A", FONT_R, (555, 148)),
        ("FCN:", 16, "#A5D6A7", FONT_B, (80, 350)),
        ("Conv", 11, "white", FONT_R, (92, 388)),
        ("Pool", 11, "white", FONT_R, (178, 388)),
        ("Conv", 11, "white", FONT_R, (250, 388)),
        ("Pool", 11, "white", FONT_R, (325, 388)),
        ("Conv1x1", 11, "#A5D6A7", FONT_R, (390, 388)),
        ("Upsample", 11, "#FFE082", FONT_R, (486, 388)),
        ("Mapa", 11, "#A5D6A7", FONT_R, (595, 388)),
        (
            "FC: spłaszcza 3D→1D, wymusza stały rozmiar → 1 etykieta",
            16,
            "#EF9A9A",
            FONT_R,
            (80, 250),
        ),
        (
            "Conv1x1: działa per piksel x kanały → DOWOLNY rozmiar → mapa klasy",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 460),
        ),
        (
            "KROK 2: Skip connections — łączą wczesne detale z późną abstrakcją",
            17,
            "#64B5F6",
            FONT_R,
            (80, 510),
        ),
        (
            "Wczesne warstwy = krawędzie, tekstury | Późne = koncepty obiektów",
            15,
            "#78909C",
            FONT_R,
            (80, 545),
        ),
        (
            "FCN = PIERWSZA sieć end-to-end do segmentacji per-piksel!",
            18,
            "white",
            FONT_R,
            (80, 590),
        ),
        (
            "Mnemonik: FC → Conv 1x1 = otwieramy bramkę dla DOWOLNEGO rozmiaru",
            16,
            "#FFE082",
            FONT_R,
            (80, 640),
        ),
    ]
    slides = [_compose_slide(fcn_clip, labels, dur)]

    # Slide 2: FCN skip connections step by step
    skip_lines = [
        ("FCN: Skip Connections — krok po kroku", 26, "#FFE082", FONT_B, (80, 30)),
        (
            "1. Encoder zmniejsza: 224→112→56→28→14 (pooling)",
            18,
            "#64B5F6",
            FONT_R,
            (100, 100),
        ),
        (
            "   Każdy pooling traci detale przestrzenne (dokładne krawędzie)",
            15,
            "#78909C",
            FONT_R,
            (100, 135),
        ),
        (
            "2. Decoder powiększa: 14→28→56→112→224 (upsample/deconv)",
            18,
            "#A5D6A7",
            FONT_R,
            (100, 190),
        ),
        (
            "   Upsample ODGADUJE piksele — rozmyty wynik!",
            15,
            "#78909C",
            FONT_R,
            (100, 225),
        ),
        (
            "3. Skip connections: dodaj cechy z encodera do decodera",
            18,
            "#FFE082",
            FONT_R,
            (100, 280),
        ),
        (
            "   Wczesne cechy = GDZIE (precyzyjne krawędzie)",
            15,
            "#64B5F6",
            FONT_R,
            (100, 315),
        ),
        (
            "   Późne cechy = CO (abstrakcyjne koncepty)",
            15,
            "#A5D6A7",
            FONT_R,
            (100, 345),
        ),
        (
            "   Skip = daje decoderowi OBA → ostry wynik!",
            15,
            "#FFE082",
            FONT_R,
            (100, 375),
        ),
        (
            "Warianty: FCN-32s (brak skip, rozmyty) → FCN-16s → FCN-8s (najlepszy)",
            16,
            "#B0BEC5",
            FONT_R,
            (80, 440),
        ),
        (
            "FCN-32s: upsample 32x naraz → ROZMYTE granice",
            15,
            "#EF9A9A",
            FONT_R,
            (100, 485),
        ),
        (
            "FCN-16s: skip z pool4 + upsample 16x → lepiej",
            15,
            "#FFE082",
            FONT_R,
            (100, 520),
        ),
        (
            "FCN-8s:  skip z pool3+pool4 + upsample 8x → OSTRE granice!",
            15,
            "#A5D6A7",
            FONT_R,
            (100, 555),
        ),
        (
            "Im więcej skip connections → tym więcej "
            "detali z encodera → ostrzejszy wynik",
            17,
            "white",
            FONT_R,
            (80, 620),
        ),
    ]
    slides.append(_text_slide(skip_lines, duration=STEP_DUR + 1))

    return slides
