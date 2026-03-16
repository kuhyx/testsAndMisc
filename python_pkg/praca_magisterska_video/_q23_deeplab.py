"""DeepLab architecture animations for Q23 segmentation video."""

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
)


# ── DeepLab Architecture ─────────────────────────────────────────
def _make_dilated_frame(t: float) -> np.ndarray:
    """Render a dilated convolution comparison frame."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = BG_COLOR
    progress = min(t / (STEP_DUR * 0.7), 1.0)

    cell = 36
    grids = [
        (
            "rate=1",
            60,
            [
                (0, 0),
                (0, 1),
                (0, 2),
                (1, 0),
                (1, 1),
                (1, 2),
                (2, 0),
                (2, 1),
                (2, 2),
            ],
        ),
        (
            "rate=2",
            420,
            [
                (0, 0),
                (0, 2),
                (0, 4),
                (2, 0),
                (2, 2),
                (2, 4),
                (4, 0),
                (4, 2),
                (4, 4),
            ],
        ),
        (
            "rate=3",
            820,
            [
                (0, 0),
                (0, 3),
                (0, 6),
                (3, 0),
                (3, 3),
                (3, 6),
                (6, 0),
                (6, 3),
                (6, 6),
            ],
        ),
    ]

    for gi, (_label, gx, positions) in enumerate(grids):
        if progress < gi * 0.3:
            break
        gy = 180
        grid_size = 7
        for r in range(grid_size):
            for c in range(grid_size):
                x = gx + c * cell
                y = gy + r * cell
                frame[y : y + cell - 2, x : x + cell - 2] = (35, 40, 55)
        for r, c in positions:
            x = gx + c * cell
            y = gy + r * cell
            frame[y : y + cell - 2, x : x + cell - 2] = (70, 130, 200)
            frame[y : y + 2, x : x + cell - 2] = (120, 180, 255)
            frame[y + cell - 4 : y + cell - 2, x : x + cell - 2] = (120, 180, 255)

    return frame


def _make_aspp_frame(t: float) -> np.ndarray:
    """Render a single ASPP module animation frame."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = BG_COLOR
    progress = min(t / (STEP_DUR * 0.7), 1.0)

    frame[250:330, 50:130] = (70, 130, 200)
    frame[250:252, 50:130] = (120, 180, 255)
    frame[328:330, 50:130] = (120, 180, 255)

    branches = [
        ("1x1 conv", 250, (200, 170), (100, 40), (80, 200, 120)),
        ("rate=6", 310, (200, 250), (100, 40), (200, 160, 80)),
        ("rate=12", 370, (200, 330), (100, 40), (200, 120, 60)),
        ("rate=18", 430, (200, 410), (100, 40), (180, 100, 80)),
        ("GAP", 490, (200, 490), (100, 40), (160, 80, 160)),
    ]
    n_branches = min(int(progress * 5) + 1, 5)
    for i, (_lbl, _h, (bx, by), (bw, bh), color) in enumerate(branches):
        if i < n_branches:
            frame[by : by + bh, bx : bx + bw] = color
            frame[by : by + 2, bx : bx + bw] = tuple(min(c + 50, 255) for c in color)
            ay = by + bh // 2
            frame[ay - 1 : ay + 2, 133:197] = (150, 150, 170)

    concat_phase = 0.6
    if progress > concat_phase:
        frame[250:530, 380:420] = (50, 60, 80)
        frame[250:252, 380:420] = (200, 200, 100)
        frame[528:530, 380:420] = (200, 200, 100)
        for i, (_lbl, _h, (bx, by), (bw, bh), _c) in enumerate(branches):
            if i < n_branches:
                ay = by + bh // 2
                frame[ay - 1 : ay + 2, bx + bw + 3 : 378] = (150, 150, 170)

    final_conv_phase = 0.8
    if progress > final_conv_phase:
        frame[350:420, 450:550] = (100, 200, 100)
        frame[350:352, 450:550] = (150, 230, 150)
        frame[418:420, 450:550] = (150, 230, 150)
        frame[388:391, 423:448] = (150, 150, 170)

    return frame


def _deeplab_demo() -> list[CompositeVideoClip]:
    """Animate DeepLab: dilated convolution + ASPP step by step."""
    dur = STEP_DUR + 1

    # Slide 1: Regular vs Dilated convolution
    dil_clip = VideoClip(_make_dilated_frame, duration=dur).with_fps(FPS)
    labels = [
        ("DeepLab: Atrous (Dilated) Convolution", 26, "#FFE082", FONT_B, (80, 20)),
        (
            "KROK 1: Zrozum dilated convolution — filtr z DZIURAMI",
            18,
            "#A5D6A7",
            FONT_R,
            (80, 60),
        ),
        ("rate=1 (zwykła)", 14, "#64B5F6", FONT_B, (60, 160)),
        ("RF = 3x3", 14, "#64B5F6", FONT_R, (60, 440)),
        ("9 wag, kontekst 3px", 12, "#78909C", FONT_R, (60, 470)),
        ("rate=2 (dilated)", 14, "#FFE082", FONT_B, (420, 160)),
        ("RF = 5x5", 14, "#FFE082", FONT_R, (420, 440)),
        ("9 wag, kontekst 5px!", 12, "#78909C", FONT_R, (420, 470)),
        ("rate=3 (dilated)", 14, "#A5D6A7", FONT_B, (820, 160)),
        ("RF = 7x7", 14, "#A5D6A7", FONT_R, (820, 440)),
        ("9 wag, kontekst 7px!", 12, "#78909C", FONT_R, (820, 470)),
        (
            "Niebieski = pozycja wag filtra 3x3 | Szary = pominięte (dziury)",
            15,
            "#B0BEC5",
            FONT_R,
            (80, 510),
        ),
        (
            "TE SAME 9 wag → WIĘKSZE pole widzenia "
            "→ lepszy kontekst BEZ dodatkowych parametrów!",
            16,
            "white",
            FONT_R,
            (80, 550),
        ),
        (
            "Mnemonik: DZIURY w filtrze — à trous = z dziurami (fr.)",
            16,
            "#FFE082",
            FONT_R,
            (80, 600),
        ),
    ]
    slides = [_compose_slide(dil_clip, labels, dur)]

    # Slide 2: ASPP module step by step
    aspp_clip = VideoClip(_make_aspp_frame, duration=dur).with_fps(FPS)
    labels2 = [
        (
            "DeepLab: ASPP (Atrous Spatial Pyramid Pooling)",
            24,
            "#FFE082",
            FONT_B,
            (80, 20),
        ),
        (
            "KROK 2: Multi-scale — analizuj obraz na WIELU skalach naraz",
            17,
            "#A5D6A7",
            FONT_R,
            (80, 60),
        ),
        ("Wejście", 13, "#64B5F6", FONT_B, (55, 235)),
        ("Conv 1x1", 12, "white", FONT_R, (210, 178)),
        ("Dilated r=6", 12, "white", FONT_R, (205, 258)),
        ("Dilated r=12", 12, "white", FONT_R, (203, 338)),
        ("Dilated r=18", 12, "white", FONT_R, (203, 418)),
        ("GAP (global)", 12, "white", FONT_R, (205, 498)),
        ("Concat", 13, "#FFE082", FONT_B, (381, 537)),
        ("Conv", 13, "#A5D6A7", FONT_B, (470, 425)),
        (
            "5 gałęzi RÓWNOLEGŁYCH → różne skale kontekstu:",
            16,
            "#B0BEC5",
            FONT_R,
            (550, 170),
        ),
        ("  1x1: kontekst punktowy (piksel)", 14, "#A5D6A7", FONT_R, (560, 210)),
        ("  r=6: kontekst lokalny (~13px)", 14, "#FFE082", FONT_R, (560, 245)),
        ("  r=12: kontekst średni (~25px)", 14, "#FFE082", FONT_R, (560, 280)),
        ("  r=18: kontekst szeroki (~37px)", 14, "#FFE082", FONT_R, (560, 315)),
        ("  GAP: kontekst GLOBALNY (cały obraz)", 14, "#CE93D8", FONT_R, (560, 350)),
        ("Concat → 1x1 conv → mapa segmentacji", 16, "#A5D6A7", FONT_R, (550, 400)),
        (
            "Efekt: sieć widzi OD piksela DO całego obrazu naraz!",
            17,
            "white",
            FONT_R,
            (80, 600),
        ),
        (
            "Mnemonik: ASPP = Piramida z DZIURAMI, patrzy na 5 skal jednocześnie",
            15,
            "#FFE082",
            FONT_R,
            (80, 645),
        ),
    ]
    slides.append(_compose_slide(aspp_clip, labels2, dur))

    return slides
