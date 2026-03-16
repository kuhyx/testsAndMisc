"""RPN anchor boxes and YOLO grid detection."""

from __future__ import annotations

from _q24_common import (
    BG_COLOR,
    FONT_B,
    FONT_R,
    FPS,
    STEP_DUR,
    H,
    W,
    _tc,
    _text_slide,
)
from moviepy import CompositeVideoClip, VideoClip
from moviepy.video.fx import FadeIn, FadeOut
import numpy as np


# ── RPN + Anchor Boxes ───────────────────────────────────────────
def _rpn_anchors_demo() -> list[CompositeVideoClip]:
    """Animate RPN and anchor boxes: Faster R-CNN innovation."""
    slides = []

    # Slide 1: Anchor boxes concept
    def make_anchors_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.7), 1.0)

        # Draw feature map grid point with multiple anchors
        cx, cy = 350, 360  # center point on feature map

        # Draw a "feature map" grid background
        cell = 60
        for r in range(-3, 4):
            for c in range(-3, 4):
                x = cx + c * cell - cell // 2
                y = cy + r * cell - cell // 2
                frame[y : y + cell - 1, x : x + cell - 1] = (30, 35, 48)

        # Center point highlighted
        frame[cy - 5 : cy + 5, cx - 5 : cx + 5] = (255, 200, 50)

        # Draw anchors around center: 3 sizes x 3 ratios = 9
        anchor_specs = [
            (30, 30, (200, 80, 80)),  # small 1:1
            (20, 40, (200, 60, 60)),  # small 1:2
            (40, 20, (180, 60, 60)),  # small 2:1
            (60, 60, (80, 200, 80)),  # medium 1:1
            (40, 80, (60, 180, 60)),  # medium 1:2
            (80, 40, (60, 160, 60)),  # medium 2:1
            (90, 90, (80, 80, 200)),  # large 1:1
            (60, 120, (60, 60, 180)),  # large 1:2
            (120, 60, (60, 60, 160)),  # large 2:1
        ]
        n_anchors = min(int(progress * 9) + 1, 9)
        for i in range(n_anchors):
            hw, hh, color = anchor_specs[i]
            x1 = max(0, cx - hw)
            y1 = max(0, cy - hh)
            x2 = min(W - 1, cx + hw)
            y2 = min(H - 1, cy + hh)
            for tt in range(2):
                frame[y1 - tt : y2 + tt, x1 - tt : x1 - tt + 2] = color
                frame[y1 - tt : y2 + tt, x2 + tt - 2 : x2 + tt] = color
                frame[y1 - tt : y1 - tt + 2, x1 - tt : x2 + tt] = color
                frame[y2 + tt - 2 : y2 + tt, x1 - tt : x2 + tt] = color

        return frame

    anch_clip = VideoClip(make_anchors_frame, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
    labels = [
        ("Anchor Boxes + RPN (Faster R-CNN)", 26, "#FFE082", FONT_B, (80, 20)),
        (
            "KROK 1: Anchory = predefiniowane kształty w każdej pozycji",
            17,
            "#A5D6A7",
            FONT_R,
            (80, 60),
        ),
        (
            "3 rozmiary x 3 proporcje = 9 anchorów per punkt",
            16,
            "#B0BEC5",
            FONT_R,
            (80, 90),
        ),
        ("Małe (1:1, 1:2, 2:1)", 14, "#EF9A9A", FONT_R, (750, 170)),
        ("Średnie (1:1, 1:2, 2:1)", 14, "#A5D6A7", FONT_R, (750, 210)),
        ("Duże (1:1, 1:2, 2:1)", 14, "#64B5F6", FONT_R, (750, 250)),
        ("Żółty punkt = pozycja", 14, "#FFE082", FONT_R, (750, 310)),
        ("na feature mapie", 14, "#FFE082", FONT_R, (750, 335)),
        ("Sieć NIE predykuje bbox od zera!", 16, "white", FONT_R, (80, 530)),
        (
            "Predykuje OFFSET od najbliższego anchora: (Δx, Δy, Δw, Δh)",
            16,
            "#FFE082",
            FONT_R,
            (80, 565),
        ),
        (
            "+ P(obiekt) = 'czy w tym anchorze jest coś?'",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 600),
        ),
        (
            "Mnemonik: Anchor = KOTWICA — sieć dopasowuje bbox do kotwicy",
            15,
            "#78909C",
            FONT_R,
            (80, 645),
        ),
    ]
    text_clips: list[VideoClip] = [anch_clip]
    for text, fs, color, font, pos in labels:
        tc = (
            _tc(text=text, font_size=fs, color=color, font=font)
            .with_duration(dur)
            .with_position(pos)
        )
        text_clips.append(tc)
    slides.append(
        CompositeVideoClip(text_clips, size=(W, H)).with_effects(
            [FadeIn(0.3), FadeOut(0.3)]
        )
    )

    # Slide 2: RPN step by step
    rpn_lines = [
        (
            "RPN: Region Proposal Network — krok po kroku",
            24,
            "#FFE082",
            FONT_B,
            (80, 30),
        ),
        (
            "Zastępuje Selective Search SIECIĄ NEURONOWĄ (end-to-end!)",
            17,
            "#B0BEC5",
            FONT_R,
            (80, 85),
        ),
        ("", 10, "white", FONT_R, (80, 110)),
        (
            "1. Backbone (ResNet) przetwarza obraz → feature mapa [40x60x256]",
            16,
            "#64B5F6",
            FONT_R,
            (100, 140),
        ),
        (
            "2. Filtr 3x3 przesuwa się po feature mapie",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 180),
        ),
        (
            "3. W KAŻDEJ pozycji (x,y) rozważ k=9 anchorów:",
            16,
            "#FFE082",
            FONT_R,
            (100, 220),
        ),
        ("   → P(obiekt) — 'czy tu jest coś?'", 15, "white", FONT_R, (120, 255)),
        ("   → (Δx, Δy, Δw, Δh) — poprawka pozycji", 15, "white", FONT_R, (120, 285)),
        (
            "4. 40x60 pozycji x 9 anchorów = 21 600 kandydatów!",
            16,
            "#EF9A9A",
            FONT_R,
            (100, 325),
        ),
        (
            "5. Weź ~300 z najwyższym P(obiekt) → ROI Pool → FC",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 365),
        ),
        ("", 10, "white", FONT_R, (100, 395)),
        ("Porównanie generowania propozycji:", 17, "white", FONT_B, (80, 420)),
        (
            "  Selective Search: ~2000 regionów, osobny algorytm, ~2 sec",
            15,
            "#EF9A9A",
            FONT_R,
            (100, 460),
        ),
        (
            "  RPN: ~300 regionów, W SIECI, ~10 ms → 200x szybciej!",
            15,
            "#A5D6A7",
            FONT_R,
            (100, 495),
        ),
        ("", 10, "white", FONT_R, (100, 520)),
        (
            "Faster R-CNN = Backbone + RPN + ROI Pool + FC — WSZYSTKO end-to-end",
            17,
            "#FFE082",
            FONT_R,
            (80, 545),
        ),
        (
            "→ 5 fps (0.2 sec/obraz) vs R-CNN 50 sec = 250x szybciej!",
            17,
            "#A5D6A7",
            FONT_R,
            (80, 585),
        ),
        (
            "Wciąż two-stage: (1) RPN generuje propozycje, (2) FC klasyfikuje",
            15,
            "#78909C",
            FONT_R,
            (80, 630),
        ),
    ]
    slides.append(_text_slide(rpn_lines, duration=STEP_DUR + 1))

    return slides


# ── YOLO ──────────────────────────────────────────────────────────
def _yolo_demo() -> list[CompositeVideoClip]:
    """Animate YOLO grid detection concept."""
    slides = []

    def make_yolo_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        progress = min(t / (STEP_DUR * 0.7), 1.0)

        # Draw image with grid overlay
        img_x, img_y = 100, 140
        img_size = 420
        grid_n = 7

        # Background "image"
        frame[img_y : img_y + img_size, img_x : img_x + img_size] = (50, 55, 70)

        # Objects in the image
        frame[img_y + 80 : img_y + 200, img_x + 50 : img_x + 180] = (
            180,
            60,
            60,
        )  # "car"
        frame[img_y + 150 : img_y + 350, img_x + 250 : img_x + 330] = (
            60,
            120,
            180,
        )  # "person"

        # Grid lines
        cell = img_size // grid_n
        for i in range(grid_n + 1):
            # Vertical
            x = img_x + i * cell
            frame[img_y : img_y + img_size, x : x + 1] = (100, 100, 120)
            # Horizontal
            y = img_y + i * cell
            frame[y : y + 1, img_x : img_x + img_size] = (100, 100, 120)

        # Highlight cells containing object centers
        car_phase = 0.3
        if progress > car_phase:
            # Car center ~ cell (1, 1)
            cx, cy = 1, 2
            hx = img_x + cx * cell
            hy = img_y + cy * cell
            frame[hy : hy + cell, hx : hx + cell] = np.clip(
                frame[hy : hy + cell, hx : hx + cell].astype(int) + 40, 0, 255
            ).astype(np.uint8)

        person_phase = 0.5
        if progress > person_phase:
            # Person center ~ cell (4, 4)
            cx, cy = 4, 4
            hx = img_x + cx * cell
            hy = img_y + cy * cell
            frame[hy : hy + cell, hx : hx + cell] = np.clip(
                frame[hy : hy + cell, hx : hx + cell].astype(int) + 40, 0, 255
            ).astype(np.uint8)

        # Bounding boxes predictions from cells
        bbox_phase = 0.6
        if progress > bbox_phase:
            # Car bbox
            for tt in range(2):
                frame[
                    img_y + 78 - tt : img_y + 202 + tt,
                    img_x + 48 - tt : img_x + 48 - tt + 2,
                ] = (255, 80, 80)
                frame[
                    img_y + 78 - tt : img_y + 202 + tt,
                    img_x + 182 + tt - 2 : img_x + 182 + tt,
                ] = (255, 80, 80)
                frame[
                    img_y + 78 - tt : img_y + 78 - tt + 2,
                    img_x + 48 - tt : img_x + 182 + tt,
                ] = (255, 80, 80)
                frame[
                    img_y + 202 + tt - 2 : img_y + 202 + tt,
                    img_x + 48 - tt : img_x + 182 + tt,
                ] = (255, 80, 80)

            # Person bbox
            for tt in range(2):
                frame[
                    img_y + 148 - tt : img_y + 352 + tt,
                    img_x + 248 - tt : img_x + 248 - tt + 2,
                ] = (80, 180, 255)
                frame[
                    img_y + 148 - tt : img_y + 352 + tt,
                    img_x + 332 + tt - 2 : img_x + 332 + tt,
                ] = (80, 180, 255)
                frame[
                    img_y + 148 - tt : img_y + 148 - tt + 2,
                    img_x + 248 - tt : img_x + 332 + tt,
                ] = (80, 180, 255)
                frame[
                    img_y + 352 + tt - 2 : img_y + 352 + tt,
                    img_x + 248 - tt : img_x + 332 + tt,
                ] = (80, 180, 255)

        return frame

    yolo_clip = VideoClip(make_yolo_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [yolo_clip]
    labels = [
        ("YOLO — You Only Look Once", 28, "#FFE082", FONT_B, (80, 20)),
        (
            "Jednoetapowy detektor: siatka SxS → wszystkie detekcje naraz!",
            18,
            "#B0BEC5",
            FONT_R,
            (80, 65),
        ),
        ("Siatka 7x7 = 49 komórek", 16, "#64B5F6", FONT_R, (600, 180)),
        ("Każda komórka predykuje:", 16, "white", FONT_R, (600, 220)),
        ("  • B bbox (x, y, w, h, conf)", 14, "#B0BEC5", FONT_R, (600, 255)),
        ("  • C klas (prawdopodobieństwa)", 14, "#B0BEC5", FONT_R, (600, 285)),
        ("Komórka odpowiada za obiekt", 14, "#A5D6A7", FONT_R, (600, 325)),
        ("którego ŚRODEK w niej wpada", 14, "#A5D6A7", FONT_R, (600, 350)),
        ("45-155 fps! (vs 5 fps Faster R-CNN)", 18, "#EF9A9A", FONT_B, (600, 400)),
        (
            "Jedno przejście przez sieć → WSZYSTKIE detekcje naraz → NMS → wynik",
            14,
            "#78909C",
            FONT_R,
            (80, 620),
        ),
        (
            "Two-stage (R-CNN): propozycje+klasyfikacja "
            "| One-stage (YOLO): bez propozycji!",
            14,
            "#90CAF9",
            FONT_R,
            (80, 655),
        ),
    ]
    for text, fs, color, font, pos in labels:
        tc = (
            _tc(text=text, font_size=fs, color=color, font=font)
            .with_duration(STEP_DUR)
            .with_position(pos)
        )
        text_clips.append(tc)

    slides.append(
        CompositeVideoClip(text_clips, size=(W, H)).with_effects(
            [FadeIn(0.3), FadeOut(0.3)]
        )
    )
    return slides
