"""R-CNN family: evolution, detailed pipeline, ROI pooling."""

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
)
from moviepy import CompositeVideoClip, VideoClip
from moviepy.video.fx import FadeIn, FadeOut
import numpy as np


# ── R-CNN Evolution ───────────────────────────────────────────────
def _rcnn_evolution() -> list[CompositeVideoClip]:
    """Animate R-CNN → Fast R-CNN → Faster R-CNN evolution."""
    slides = []

    def make_evolution_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        progress = min(t / (STEP_DUR * 0.8), 1.0)

        # Three rows: R-CNN, Fast R-CNN, Faster R-CNN
        models = [
            (
                "R-CNN (2014)",
                50,
                [
                    ("Selective\nSearch", (200, 150), (100, 50), (120, 100, 60)),
                    ("2000x\nCNN", (350, 150), (80, 50), (180, 60, 60)),
                    ("2000x\nSVM", (480, 150), (80, 50), (180, 60, 60)),
                    ("NMS", (610, 150), (60, 50), (100, 140, 100)),
                ],
                "50 sec/obraz!",
            ),
            (
                "Fast R-CNN (2015)",
                300,
                [
                    ("Selective\nSearch", (200, 150), (100, 50), (120, 100, 60)),
                    ("1x CNN\n(cały obraz)", (350, 150), (100, 50), (80, 140, 200)),
                    ("ROI Pool\n(2000)", (500, 150), (90, 50), (200, 160, 80)),
                    ("FC", (640, 150), (50, 50), (100, 140, 100)),
                ],
                "2 sec/obraz",
            ),
            (
                "Faster R-CNN (2015)",
                300,
                [
                    ("CNN\nbackbone", (200, 150), (90, 50), (80, 140, 200)),
                    ("RPN\n(~300)", (340, 150), (80, 50), (200, 120, 60)),
                    ("ROI Pool", (470, 150), (80, 50), (200, 160, 80)),
                    ("FC", (600, 150), (50, 50), (100, 140, 100)),
                ],
                "0.2 sec → 5 fps!",
            ),
        ]

        n_models = int(progress * 3) + 1

        for mi, (_name, base_y, stages, _speed) in enumerate(models):
            if mi >= n_models:
                break
            for _label, (bx, by_off), (bw, bh), color in stages:
                by = base_y + by_off - 150
                frame[by : by + bh, bx : bx + bw] = color
                frame[by : by + 2, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )

            # Arrows between stages
            for si in range(len(stages) - 1):
                sx = stages[si][1][0] + stages[si][2][0]
                ex = stages[si + 1][1][0]
                ay = base_y + 25
                frame[ay - 1 : ay + 2, sx + 3 : ex - 3] = (150, 150, 170)

        return frame

    evo_clip = VideoClip(make_evolution_frame, duration=STEP_DUR + 1).with_fps(FPS)
    text_clips: list[VideoClip] = [evo_clip]
    labels = [
        ("Ewolucja R-CNN — CORAZ MNIEJ MARNOWANIA", 28, "#FFE082", FONT_B, (80, 20)),
        ("R-CNN (2014)", 20, "#EF9A9A", FONT_B, (50, 80)),
        ("50 sec/obraz (2000x forward pass!)", 14, "#EF9A9A", FONT_R, (720, 100)),
        ("Fast R-CNN (2015)", 20, "#64B5F6", FONT_B, (50, 330)),
        ("2 sec/obraz (CNN raz + ROI Pool)", 14, "#64B5F6", FONT_R, (720, 350)),
        ("Faster R-CNN (2015)", 20, "#A5D6A7", FONT_B, (50, 580)),
        ("0.2 sec → 5 fps (RPN w sieci!)", 14, "#A5D6A7", FONT_R, (720, 600)),
        (
            "Kluczowe innowacje: ROI Pooling → stały rozmiar "
            "| RPN → propozycje w sieci",
            14,
            "#78909C",
            FONT_R,
            (80, 660),
        ),
    ]
    for text, fs, color, font, pos in labels:
        tc = (
            _tc(text=text, font_size=fs, color=color, font=font)
            .with_duration(STEP_DUR + 1)
            .with_position(pos)
        )
        text_clips.append(tc)

    slides.append(
        CompositeVideoClip(text_clips, size=(W, H)).with_effects(
            [FadeIn(0.3), FadeOut(0.3)]
        )
    )
    return slides


# ── R-CNN Detailed Pipeline ──────────────────────────────────────
def _rcnn_detailed() -> list[CompositeVideoClip]:
    """Animate R-CNN step-by-step pipeline in detail."""
    slides = []

    # Slide 1: R-CNN pipeline step by step
    def make_rcnn_pipeline(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.8), 1.0)

        # Step boxes arranged vertically with arrows
        steps = [
            ((80, 130), (200, 55), (120, 100, 60), "1. Selective Search"),
            ((80, 230), (200, 55), (180, 60, 60), "2. Wytnij 2000 regionów"),
            ((80, 330), (200, 55), (70, 130, 200), "3. CNN per region"),
            ((80, 430), (200, 55), (200, 100, 80), "4. SVM klasyfikuje"),
            ((80, 530), (200, 55), (100, 180, 100), "5. Bbox regresja + NMS"),
        ]
        n_steps = min(int(progress * 5) + 1, 5)
        for i, ((bx, by), (bw, bh), color, _lbl) in enumerate(steps):
            if i < n_steps:
                frame[by : by + bh, bx : bx + bw] = color
                frame[by : by + 2, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                # Arrow down
                arrow_limit = 4
                if i < arrow_limit:
                    ax = bx + bw // 2
                    ay = by + bh + 5
                    frame[ay : ay + 20, ax - 1 : ax + 2] = (150, 150, 170)

        # Illustration: many overlapping regions from Selective Search
        overlay_phase = 0.2
        if progress > overlay_phase:
            rng_local = np.random.default_rng(42)
            n_boxes = min(int((progress - 0.2) * 15), 8)
            for i in range(n_boxes):
                rx = 500 + rng_local.integers(-30, 100)
                ry = 200 + rng_local.integers(-20, 120)
                rw = 60 + rng_local.integers(0, 80)
                rh = 50 + rng_local.integers(0, 70)
                c = (80 + i * 15, 100 + i * 10, 60 + i * 20)
                for tt in range(2):
                    frame[ry - tt : ry + rh + tt, rx - tt : rx - tt + 2] = c
                    frame[ry - tt : ry + rh + tt, rx + rw + tt - 2 : rx + rw + tt] = c
                    frame[ry - tt : ry - tt + 2, rx - tt : rx + rw + tt] = c
                    frame[ry + rh + tt - 2 : ry + rh + tt, rx - tt : rx + rw + tt] = c

        return frame

    rcnn_clip = VideoClip(make_rcnn_pipeline, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
    labels = [
        ("R-CNN: krok po kroku (2014, Girshick)", 26, "#FFE082", FONT_B, (80, 20)),
        ("Pipeline detekcji two-stage", 16, "#B0BEC5", FONT_R, (80, 60)),
        ("Selective Search", 11, "white", FONT_R, (105, 145)),
        ("2000 regionów", 11, "white", FONT_R, (105, 245)),
        ("CNN per region", 11, "white", FONT_R, (105, 345)),
        ("SVM klasyfikuje", 11, "white", FONT_R, (105, 445)),
        ("Regresja + NMS", 11, "white", FONT_R, (105, 545)),
        ("~2000 propozycji regionów", 14, "#78909C", FONT_R, (500, 155)),
        ("(inteligentne łączenie", 13, "#78909C", FONT_R, (500, 180)),
        ("podobnych fragmentów)", 13, "#78909C", FONT_R, (500, 200)),
        ("Problem: 2000 x CNN forward pass", 16, "#EF9A9A", FONT_R, (400, 400)),
        ("= 50 SEKUND na obraz!", 18, "#EF9A9A", FONT_B, (400, 430)),
        ("CNN liczy cechy per region OSOBNO", 14, "#EF9A9A", FONT_R, (400, 470)),
        (
            "→ regiony się nakładają → obliczenia się powtarzają!",
            14,
            "#EF9A9A",
            FONT_R,
            (400, 495),
        ),
        (
            "Rozwiązanie: CNN raz na cały obraz → Fast R-CNN →",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 620),
        ),
    ]
    text_clips: list[VideoClip] = [rcnn_clip]
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

    return slides


# ── ROI Pooling ──────────────────────────────────────────────────


def _draw_roi_pool_grid(frame: np.ndarray) -> None:
    """Draw the 3x3 ROI pool grid with max-pooled feature values."""
    out_x, out_y = 400, 220
    out_cell = 50
    out_n = 3
    roi_r1, roi_c1 = 2, 1
    roi_r2, roi_c2 = 6, 5
    roi_h = roi_r2 - roi_r1
    roi_w = roi_c2 - roi_c1
    for r in range(out_n):
        for c in range(out_n):
            x = out_x + c * out_cell
            y = out_y + r * out_cell

            # Compute the max from corresponding region
            src_r1 = roi_r1 + r * roi_h // out_n
            src_r2 = roi_r1 + (r + 1) * roi_h // out_n
            src_c1 = roi_c1 + c * roi_w // out_n
            src_c2 = roi_c1 + (c + 1) * roi_w // out_n
            max_val = 0
            for sr in range(src_r1, src_r2):
                for sc in range(src_c1, src_c2):
                    v = 30 + ((sr * 7 + sc * 13 + 42) % 40)
                    max_val = max(max_val, v)

            frame[y : y + out_cell - 2, x : x + out_cell - 2] = (
                max_val,
                max_val + 20,
                max_val + 40,
            )
            frame[y : y + 2, x : x + out_cell - 2] = (80, 200, 120)
            frame[y + out_cell - 4 : y + out_cell - 2, x : x + out_cell - 2] = (
                80,
                200,
                120,
            )


def _make_roi_frame(t: float) -> np.ndarray:
    """Render a single frame for the ROI pooling animation."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = BG_COLOR
    progress = min(t / (STEP_DUR * 0.7), 1.0)

    # Left: feature map with ROI highlighted
    fm_x, fm_y = 60, 180
    fm_cell = 30
    fm_grid = 8
    for r in range(fm_grid):
        for c in range(fm_grid):
            x = fm_x + c * fm_cell
            y = fm_y + r * fm_cell
            # Random-looking feature values
            val = 30 + ((r * 7 + c * 13 + 42) % 40)
            frame[y : y + fm_cell - 1, x : x + fm_cell - 1] = (
                val,
                val + 10,
                val + 20,
            )

    # ROI region highlighted
    roi_r1, roi_c1 = 2, 1
    roi_r2, roi_c2 = 6, 5
    for tt in range(3):
        ry1 = fm_y + roi_r1 * fm_cell - tt
        ry2 = fm_y + roi_r2 * fm_cell + tt
        rx1 = fm_x + roi_c1 * fm_cell - tt
        rx2 = fm_x + roi_c2 * fm_cell + tt
        frame[ry1:ry2, rx1 : rx1 + 2] = (255, 200, 50)
        frame[ry1:ry2, rx2 - 2 : rx2] = (255, 200, 50)
        frame[ry1 : ry1 + 2, rx1:rx2] = (255, 200, 50)
        frame[ry2 - 2 : ry2, rx1:rx2] = (255, 200, 50)

    # Arrow
    arrow_phase = 0.3
    if progress > arrow_phase:
        frame[300:303, 310:380] = (150, 150, 170)

    # Middle: ROI divided into 3x3 grid (output_size)
    grid_phase = 0.3
    if progress > grid_phase:
        _draw_roi_pool_grid(frame)

    # Arrow to FC
    fc_phase = 0.6
    if progress > fc_phase:
        frame[300:303, 560:630] = (150, 150, 170)
        # FC box
        frame[270:340, 650:730] = (200, 100, 80)
        frame[270:272, 650:730] = (240, 140, 120)
        frame[338:340, 650:730] = (240, 140, 120)

    return frame


def _roi_pooling_demo() -> list[CompositeVideoClip]:
    """Animate ROI Pooling: key Fast R-CNN innovation."""
    slides = []

    roi_clip = VideoClip(_make_roi_frame, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
    labels = [
        ("ROI Pooling: kluczowa innowacja Fast R-CNN", 26, "#FFE082", FONT_B, (80, 20)),
        (
            "KROK 1: CNN raz na CAŁY obraz → feature mapa",
            17,
            "#64B5F6",
            FONT_R,
            (80, 60),
        ),
        (
            "KROK 2: Wytnij ROI z feature mapy (nie z obrazu!)",
            17,
            "#FFE082",
            FONT_R,
            (80, 90),
        ),
        (
            "KROK 3: Siatkuj ROI na 3x3 → max pool per komórka → stały rozmiar",
            17,
            "#A5D6A7",
            FONT_R,
            (80, 120),
        ),
        ("Feature mapa", 14, "#64B5F6", FONT_B, (60, 160)),
        ("ROI (żółta ramka)", 13, "#FFE082", FONT_R, (60, 440)),
        ("ROI Pool 3x3", 14, "#A5D6A7", FONT_B, (400, 195)),
        ("(max z komórki)", 13, "#78909C", FONT_R, (400, 380)),
        ("FC", 14, "white", FONT_B, (670, 280)),
        (
            "Problem: ROI mają RÓŻNE rozmiary, FC wymaga STAŁEGO",
            15,
            "#B0BEC5",
            FONT_R,
            (80, 500),
        ),
        (
            "ROI Pooling: dzieli ROI na siatkę, max pool → STAŁY rozmiar!",
            16,
            "white",
            FONT_R,
            (80, 535),
        ),
        (
            "Fast R-CNN: CNN raz → 1 feature mapa → "
            "ROI Pool 2000 regionów → 25x szybciej!",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 580),
        ),
        (
            "(R-CNN: 2000x CNN = 50s | Fast R-CNN: 1xCNN + ROI Pool = 2s)",
            15,
            "#EF9A9A",
            FONT_R,
            (80, 620),
        ),
    ]
    text_clips: list[VideoClip] = [roi_clip]
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
    return slides
