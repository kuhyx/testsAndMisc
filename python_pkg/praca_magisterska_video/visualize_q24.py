"""MoviePy visualization for PYTANIE 24: Object Detection.

Creates animated video demonstrating:
- What detection is (bounding box + class + confidence)
- HOG + SVM pipeline (gradient → histogram → classify)
- Viola-Jones (Haar features, integral image, cascade)
- R-CNN evolution (R-CNN → Fast → Faster)
- YOLO one-stage detection
- Building a detector from a classifier
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"

from moviepy import (
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx import FadeIn, FadeOut

# ── Constants ─────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24
STEP_DUR = 7.0
HEADER_DUR = 4.0
FONT_B = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/TTF/DejaVuSans.ttf"
OUTPUT_DIR = Path(__file__).resolve().parent / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = str(OUTPUT_DIR / "q24_object_detection.mp4")

BG_COLOR = (15, 20, 35)


def _tc(**kwargs: object) -> TextClip:
    """TextClip wrapper that adds enough bottom margin to prevent clipping."""
    fs = kwargs.get("font_size", 24)
    m = int(fs) // 3 + 2
    kwargs["margin"] = (0, m)
    return TextClip(**kwargs)


def _make_header(
    title: str, subtitle: str, duration: float = HEADER_DUR
) -> CompositeVideoClip:
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(duration)
    t = (
        _tc(
            text=title,
            font_size=48,
            color="white",
            font=FONT_B,
        )
        .with_duration(duration)
        .with_position(("center", 260))
    )
    s = (
        _tc(
            text=subtitle,
            font_size=24,
            color="#90CAF9",
            font=FONT_R,
        )
        .with_duration(duration)
        .with_position(("center", 340))
    )
    return CompositeVideoClip([bg, t, s], size=(W, H)).with_effects(
        [FadeIn(0.5), FadeOut(0.5)]
    )


# ── Detection concept ────────────────────────────────────────────
def _detection_concept() -> list[CompositeVideoClip]:
    """Show what detection is: bounding box + class + confidence."""
    slides = []

    def make_det_frame(_t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        # Draw a "scene" with colored rectangles representing objects
        # Sky background area
        frame[140:500, 100:700] = (40, 50, 70)

        # "Car" object
        frame[350:430, 150:320] = (180, 60, 60)
        # "Person" object
        frame[280:440, 450:520] = (60, 120, 180)
        # "Tree" object
        frame[200:400, 580:650] = (40, 130, 50)

        # Bounding boxes (with labels drawn as colored borders)
        # Car bbox
        for thickness in range(3):
            t = thickness
            frame[348 - t : 432 + t, 148 - t : 148 - t + 2] = (255, 80, 80)
            frame[348 - t : 432 + t, 322 + t - 2 : 322 + t] = (255, 80, 80)
            frame[348 - t : 348 - t + 2, 148 - t : 322 + t] = (255, 80, 80)
            frame[432 + t - 2 : 432 + t, 148 - t : 322 + t] = (255, 80, 80)

        # Person bbox
        for thickness in range(3):
            t = thickness
            frame[278 - t : 442 + t, 448 - t : 448 - t + 2] = (80, 180, 255)
            frame[278 - t : 442 + t, 522 + t - 2 : 522 + t] = (80, 180, 255)
            frame[278 - t : 278 - t + 2, 448 - t : 522 + t] = (80, 180, 255)
            frame[442 + t - 2 : 442 + t, 448 - t : 522 + t] = (80, 180, 255)

        # Tree bbox
        for thickness in range(3):
            t = thickness
            frame[198 - t : 402 + t, 578 - t : 578 - t + 2] = (80, 220, 100)
            frame[198 - t : 402 + t, 652 + t - 2 : 652 + t] = (80, 220, 100)
            frame[198 - t : 198 - t + 2, 578 - t : 652 + t] = (80, 220, 100)
            frame[402 + t - 2 : 402 + t, 578 - t : 652 + t] = (80, 220, 100)

        # Comparison boxes on right side
        # Classification
        frame[180:260, 800:1150] = (35, 45, 65)
        # Detection
        frame[290:370, 800:1150] = (35, 45, 65)
        # Segmentation
        frame[400:480, 800:1150] = (35, 45, 65)

        return frame

    det_clip = VideoClip(make_det_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [det_clip]
    labels = [
        ("Detekcja obiektów — co to jest?", 28, "#FFE082", FONT_B, (100, 20)),
        ("Wynik: (klasa, bounding box, pewność)", 20, "#B0BEC5", FONT_R, (100, 65)),
        ("samochód 95%", 14, "#EF9A9A", FONT_B, (150, 340)),
        ("osoba 88%", 14, "#64B5F6", FONT_B, (450, 268)),
        ("drzewo 72%", 14, "#A5D6A7", FONT_B, (580, 188)),
        ("Klasyfikacja: cały obraz → 1 etykieta", 15, "#78909C", FONT_R, (810, 210)),
        ("Detekcja: bbox + klasa + pewność", 15, "#FFE082", FONT_R, (810, 320)),
        ("Segmentacja: maska per piksel", 15, "#78909C", FONT_R, (810, 430)),
        ("← granulacja rośnie →", 14, "#90CAF9", FONT_R, (810, 520)),
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


# ── HOG + SVM pipeline ───────────────────────────────────────────
def _hog_svm_demo() -> list[CompositeVideoClip]:
    """Animate HOG feature computation and SVM classification."""
    slides = []

    def make_hog_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        progress = min(t / (STEP_DUR * 0.8), 1.0)

        # Pipeline stages as boxes with arrows
        stages = [
            ("Gradient", (80, 250), (130, 80), (100, 160, 220)),
            ("Orientacja", (260, 250), (130, 80), (80, 180, 140)),
            ("Komórki 8x8", (440, 250), (130, 80), (200, 160, 80)),
            ("Bloki 2x2", (620, 250), (130, 80), (200, 120, 60)),
            ("Normalizacja", (800, 250), (130, 80), (180, 100, 80)),
            ("SVM", (980, 250), (130, 80), (220, 80, 80)),
        ]

        n_active = int(progress * len(stages)) + 1

        for i, (_label, (sx, sy), (sw, sh), color) in enumerate(stages):
            if i < n_active:
                frame[sy : sy + sh, sx : sx + sw] = color
                # Border
                frame[sy : sy + 2, sx : sx + sw] = tuple(
                    min(c + 60, 255) for c in color
                )
                frame[sy + sh - 2 : sy + sh, sx : sx + sw] = tuple(
                    min(c + 60, 255) for c in color
                )

                # Arrow to next
                if i < len(stages) - 1:
                    ax = sx + sw + 5
                    ay = sy + sh // 2
                    frame[ay - 1 : ay + 2, ax : ax + 20] = (150, 150, 170)

        # Show gradient computation example at bottom
        if progress > 0.2:
            # Mini pixel grid showing gradient computation
            gx, gy = 100, 430
            pixels = [50, 50, 200]
            for idx, val in enumerate(pixels):
                x = gx + idx * 50
                frame[gy : gy + 40, x : x + 40] = (val, val, val)

        return frame

    hog_clip = VideoClip(make_hog_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [hog_clip]
    labels = [
        ("HOG + SVM — pipeline detekcji pieszych", 28, "#FFE082", FONT_B, (80, 20)),
        (
            "Mnemonik: GOKBN = Gradienty→Orientacja→Komórki→Bloki→Normalizacja",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 65),
        ),
        ("Gradient: siła i kierunek zmiany jasności", 14, "#64B5F6", FONT_R, (80, 95)),
        (
            "Histogram: 9 binów (0°-180°, co 20°) per komórka 8x8",
            14,
            "#78909C",
            FONT_R,
            (80, 120),
        ),
        (
            "[50][50][200] → Gx = 200-50 = 150 = silna krawędź!",
            16,
            "#EF9A9A",
            FONT_R,
            (80, 490),
        ),
        (
            "Wektor HOG (3780 cech) → SVM: pieszy (+1) / tło (-1)",
            16,
            "white",
            FONT_R,
            (80, 540),
        ),
        (
            "Sliding window 64x128 przesuwa się po obrazie → NMS → wynik",
            16,
            "#90CAF9",
            FONT_R,
            (80, 580),
        ),
        (
            "SVM = LINIA MAKSYMALNEGO ODDECHU (max margines, support vectors)",
            16,
            "#FFE082",
            FONT_R,
            (80, 620),
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


# ── Viola-Jones ───────────────────────────────────────────────────
def _viola_jones_demo() -> list[CompositeVideoClip]:
    """Animate Viola-Jones cascade concept."""
    slides = []

    def make_cascade_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        progress = min(t / (STEP_DUR * 0.8), 1.0)

        # Draw cascade "funnel" — stages filtering out non-faces
        stages = 5
        start_width = 1000
        start_count = 10000
        x_center = W // 2

        for i in range(stages):
            stage_progress = min(progress * stages - i, 1.0)
            if stage_progress <= 0:
                break

            width = int(start_width * (1 - i * 0.18))
            int(start_count * (0.3**i))
            y = 150 + i * 100
            h_box = 60

            # Stage box
            x1 = x_center - width // 2
            frame[y : y + h_box, x1 : x1 + width] = (
                50 + i * 10,
                60 + i * 10,
                80 + i * 10,
            )
            # Border
            frame[y : y + 2, x1 : x1 + width] = (100 + i * 20, 130 + i * 15, 200)
            frame[y + h_box - 2 : y + h_box, x1 : x1 + width] = (
                100 + i * 20,
                130 + i * 15,
                200,
            )

            # Arrow down to next
            if i < stages - 1:
                frame[y + h_box + 5 : y + h_box + 25, x_center - 1 : x_center + 2] = (
                    150,
                    150,
                    170,
                )

            # Red "rejected" arrows on sides
            if i > 0:
                # Left reject arrow
                rx = x1 - 30
                ry = y + h_box // 2
                frame[ry - 1 : ry + 2, rx : rx + 25] = (200, 80, 80)

        return frame

    cascade_clip = VideoClip(make_cascade_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [cascade_clip]
    labels = [
        (
            "Viola-Jones — kaskada klasyfikatorów (2001)",
            28,
            "#FFE082",
            FONT_B,
            (80, 20),
        ),
        (
            "3 innowacje: HIC = Haar + Integral Image + Cascade",
            20,
            "#B0BEC5",
            FONT_R,
            (80, 65),
        ),
        ("Etap 1: 2 cechy Haar", 14, "#64B5F6", FONT_R, (170, 170)),
        ("Etap 2: 10 cech", 14, "#64B5F6", FONT_R, (210, 270)),
        ("Etap 3: 25 cech", 14, "#64B5F6", FONT_R, (240, 370)),
        ("Etap 4: 50 cech", 14, "#64B5F6", FONT_R, (260, 470)),
        ("→ TWARZ!", 16, "#A5D6A7", FONT_B, (590, 560)),
        (
            "SITO: 99% okien odpada w pierwszych 3 etapach → REAL-TIME!",
            16,
            "#EF9A9A",
            FONT_R,
            (80, 620),
        ),
        (
            "Haar: kontrast jasna/ciemna | Integral Image: suma prostokąta O(1) = 4 odczyty",
            14,
            "#78909C",
            FONT_R,
            (80, 655),
        ),
        ("odrzucone →", 12, "#EF9A9A", FONT_R, (60, 275)),
        ("odrzucone →", 12, "#EF9A9A", FONT_R, (60, 375)),
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
            "Kluczowe innowacje: ROI Pooling → stały rozmiar | RPN → propozycje w sieci",
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
                if i < 4:
                    ax = bx + bw // 2
                    ay = by + bh + 5
                    frame[ay : ay + 20, ax - 1 : ax + 2] = (150, 150, 170)

        # Illustration: many overlapping regions from Selective Search
        if progress > 0.2:
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
def _roi_pooling_demo() -> list[CompositeVideoClip]:
    """Animate ROI Pooling: key Fast R-CNN innovation."""
    slides = []

    def make_roi_frame(t: float) -> np.ndarray:
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
        if progress > 0.3:
            frame[300:303, 310:380] = (150, 150, 170)

        # Middle: ROI divided into 3x3 grid (output_size)
        if progress > 0.3:
            out_x, out_y = 400, 220
            out_cell = 50
            out_n = 3
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

        # Arrow to FC
        if progress > 0.6:
            frame[300:303, 560:630] = (150, 150, 170)
            # FC box
            frame[270:340, 650:730] = (200, 100, 80)
            frame[270:272, 650:730] = (240, 140, 120)
            frame[338:340, 650:730] = (240, 140, 120)

        return frame

    roi_clip = VideoClip(make_roi_frame, duration=STEP_DUR + 1).with_fps(FPS)
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
            "Fast R-CNN: CNN raz → 1 feature mapa → ROI Pool 2000 regionów → 25x szybciej!",
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
            # (half_w, half_h, color)
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
        if progress > 0.3:
            # Car center ~ cell (1, 1)
            cx, cy = 1, 2
            hx = img_x + cx * cell
            hy = img_y + cy * cell
            frame[hy : hy + cell, hx : hx + cell] = np.clip(
                frame[hy : hy + cell, hx : hx + cell].astype(int) + 40, 0, 255
            ).astype(np.uint8)

        if progress > 0.5:
            # Person center ~ cell (4, 4)
            cx, cy = 4, 4
            hx = img_x + cx * cell
            hy = img_y + cy * cell
            frame[hy : hy + cell, hx : hx + cell] = np.clip(
                frame[hy : hy + cell, hx : hx + cell].astype(int) + 40, 0, 255
            ).astype(np.uint8)

        # Bounding boxes predictions from cells
        if progress > 0.6:
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
            "Two-stage (R-CNN): propozycje+klasyfikacja | One-stage (YOLO): bez propozycji!",
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


# ── YOLO Architecture Detail ──────────────────────────────────────
def _yolo_architecture() -> list[CompositeVideoClip]:
    """Show YOLO architecture: backbone → head, output tensor."""
    slides = []

    # Slide 1: YOLO architecture breakdown
    def make_yolo_arch(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.7), 1.0)

        # Pipeline: Image → Backbone → Neck → Head → SxSx(B*5+C) tensor
        blocks = [
            ((60, 280), (100, 80), (50, 70, 90), "Obraz"),
            ((200, 280), (100, 80), (70, 130, 200), "Backbone"),
            ((340, 280), (100, 80), (200, 160, 80), "Neck"),
            ((480, 280), (100, 80), (200, 100, 60), "Head"),
            ((620, 280), (160, 80), (80, 200, 120), "SxSx(B*5+C)"),
        ]
        n_blocks = min(int(progress * 5) + 1, 5)
        for i, ((bx, by), (bw, bh), color, _lbl) in enumerate(blocks):
            if i < n_blocks:
                frame[by : by + bh, bx : bx + bw] = color
                frame[by : by + 2, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                if i < 4:
                    ax = bx + bw + 5
                    ay = by + bh // 2
                    frame[ay - 1 : ay + 2, ax : ax + 25] = (150, 150, 170)

        # Output tensor breakdown (right side)
        if progress > 0.6:
            # Show SxS grid
            gx, gy = 850, 180
            gs = 120
            gn = 4  # simplified from 7
            gc = gs // gn
            for r in range(gn):
                for c in range(gn):
                    x = gx + c * gc
                    y = gy + r * gc
                    frame[y : y + gc - 1, x : x + gc - 1] = (40, 50, 65)
            # Highlight one cell
            frame[gy + gc : gy + 2 * gc - 1, gx + gc : gx + 2 * gc - 1] = (80, 200, 120)

        return frame

    arch_clip = VideoClip(make_yolo_arch, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
    labels = [
        ("YOLO: Architektura — krok po kroku", 26, "#FFE082", FONT_B, (80, 20)),
        (
            "One-stage: JEDEN forward pass → WSZYSTKIE detekcje naraz",
            17,
            "#B0BEC5",
            FONT_R,
            (80, 60),
        ),
        ("Obraz", 13, "white", FONT_R, (85, 295)),
        ("Backbone", 13, "white", FONT_R, (215, 295)),
        ("(ResNet/", 11, "#78909C", FONT_R, (210, 370)),
        ("Darknet)", 11, "#78909C", FONT_R, (210, 390)),
        ("Neck", 13, "white", FONT_R, (365, 295)),
        ("(FPN/", 11, "#78909C", FONT_R, (360, 370)),
        ("PANet)", 11, "#78909C", FONT_R, (360, 390)),
        ("Head", 13, "white", FONT_R, (505, 295)),
        ("(conv)", 11, "#78909C", FONT_R, (500, 370)),
        ("Tensor wyjścia", 13, "#A5D6A7", FONT_R, (640, 295)),
        ("Każda komórka SxS predykuje:", 15, "#FFE082", FONT_R, (830, 320)),
        ("  B bbox x (x,y,w,h,conf)", 13, "#B0BEC5", FONT_R, (830, 350)),
        ("  + C klas (prob.)", 13, "#B0BEC5", FONT_R, (830, 375)),
        ("= SxSx(Bx5+C) tensor", 13, "#A5D6A7", FONT_R, (830, 400)),
        ("Np. 7x7x(2x5+20) = 7x7x30", 13, "#78909C", FONT_R, (830, 430)),
        (
            "Two-stage (R-CNN): (1) propozycje → (2) klasyfikacja = 2 przejścia",
            15,
            "#EF9A9A",
            FONT_R,
            (80, 470),
        ),
        (
            "One-stage (YOLO): siatka → predykcja all-in-one = 1 przejście!",
            15,
            "#A5D6A7",
            FONT_R,
            (80, 505),
        ),
        (
            "Ewolucja YOLO: v1(2016)→v3→v5→v8(2023, anchor-free, SOTA)",
            16,
            "#FFE082",
            FONT_R,
            (80, 555),
        ),
        (
            "SSD (2016): multi-scale feature maps → lepsza detekcja małych obiektów",
            15,
            "#64B5F6",
            FONT_R,
            (80, 595),
        ),
        (
            "FPN: łączy wczesne warstwy (małe obiekty) + późne (duże obiekty)",
            15,
            "#78909C",
            FONT_R,
            (80, 630),
        ),
    ]
    text_clips: list[VideoClip] = [arch_clip]
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


# ── DETR ──────────────────────────────────────────────────────────
def _detr_demo() -> list[CompositeVideoClip]:
    """Animate DETR: transformer detection, object queries, no NMS."""
    slides = []

    # Slide 1: DETR pipeline
    def make_detr_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.7), 1.0)

        # DETR pipeline: Image → Backbone → Encoder → Decoder → N predictions
        blocks = [
            ((50, 260), (80, 60), (50, 70, 90)),
            ((170, 260), (90, 60), (70, 130, 200)),
            ((300, 260), (110, 60), (200, 120, 60)),
            ((450, 260), (110, 60), (200, 80, 160)),
            ((600, 260), (120, 60), (80, 200, 120)),
        ]
        n_blocks = min(int(progress * 5) + 1, 5)
        for i, ((bx, by), (bw, bh), color) in enumerate(blocks):
            if i < n_blocks:
                frame[by : by + bh, bx : bx + bw] = color
                frame[by : by + 2, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                if i < 4:
                    ax = bx + bw + 5
                    ay = by + bh // 2
                    frame[ay - 1 : ay + 2, ax : ax + 25] = (150, 150, 170)

        # Object queries illustration (right side)
        if progress > 0.5:
            qx, qy = 800, 140
            for i in range(6):
                y = qy + i * 50
                w = 130
                active = i < 3
                color = (80, 180, 120) if active else (60, 50, 50)
                frame[y : y + 35, qx : qx + w] = color
                frame[y : y + 1, qx : qx + w] = tuple(min(c + 40, 255) for c in color)

            # Arrow from decoder to queries
            frame[285:288, 723:798] = (150, 150, 170)

        return frame

    detr_clip = VideoClip(make_detr_frame, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
    labels = [
        ("DETR: DEtection TRansformer (2020)", 26, "#FFE082", FONT_B, (80, 20)),
        (
            "Radykalnie prostszy pipeline: BEZ anchorów, BEZ NMS!",
            17,
            "#B0BEC5",
            FONT_R,
            (80, 60),
        ),
        ("Obraz", 12, "white", FONT_R, (65, 275)),
        ("Backbone", 12, "white", FONT_R, (185, 275)),
        ("Transformer", 12, "white", FONT_R, (310, 275)),
        ("Encoder", 12, "white", FONT_R, (325, 295)),
        ("Transformer", 12, "white", FONT_R, (460, 275)),
        ("Decoder", 12, "white", FONT_R, (478, 295)),
        ("N predykcji", 12, "white", FONT_R, (615, 275)),
        ("Object Queries:", 14, "#FFE082", FONT_B, (800, 115)),
        ("samochód 95%", 11, "white", FONT_R, (810, 148)),
        ("pies 88%", 11, "white", FONT_R, (810, 198)),
        ("rower 72%", 11, "white", FONT_R, (810, 248)),
        ("brak", 11, "#78909C", FONT_R, (810, 298)),
        ("brak", 11, "#78909C", FONT_R, (810, 348)),
        ("brak", 11, "#78909C", FONT_R, (810, 398)),
        ("100 wyuczonych queries", 13, "#FFE082", FONT_R, (800, 440)),
        ("→ każdy 'szuka' obiektu", 13, "#FFE082", FONT_R, (800, 465)),
    ]
    text_clips: list[VideoClip] = [detr_clip]
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

    # Slide 2: Why no NMS + Hungarian matching
    detr_details = [
        ("DETR: Dlaczego bez NMS? — krok po kroku", 24, "#FFE082", FONT_B, (80, 30)),
        (
            "Problem NMS: duplikaty detekcji → ręcznie usuwaj post-hoc",
            16,
            "#EF9A9A",
            FONT_R,
            (80, 90),
        ),
        (
            "DETR rozwiązanie: Hungarian matching (dopasowanie węgierskie)",
            17,
            "#A5D6A7",
            FONT_R,
            (80, 130),
        ),
        ("", 10, "white", FONT_R, (80, 155)),
        ("Jak to działa podczas TRENINGU:", 17, "white", FONT_B, (80, 180)),
        ("  1. Sieć daje N=100 predykcji (queries)", 15, "#64B5F6", FONT_R, (100, 220)),
        (
            "  2. Na obrazie jest np. 5 obiektów (ground truth)",
            15,
            "#64B5F6",
            FONT_R,
            (100, 255),
        ),
        (
            "  3. Hungarian matching: optymalne dopasowanie 1:1",
            15,
            "#FFE082",
            FONT_R,
            (100, 290),
        ),
        (
            "     → query_1 ↔ gt_samochód (najlepsze dopasowanie)",
            14,
            "#A5D6A7",
            FONT_R,
            (120, 325),
        ),
        ("     → query_7 ↔ gt_pies", 14, "#A5D6A7", FONT_R, (120, 355)),
        ("     → query_3 ↔ gt_rower", 14, "#A5D6A7", FONT_R, (120, 385)),
        (
            "     → pozostałe 97 queries ↔ klasa 'brak obiektu'",
            14,
            "#78909C",
            FONT_R,
            (120, 415),
        ),
        (
            "  4. Każdy obiekt ma DOKŁADNIE 1 predykcję → BRAK duplikatów!",
            15,
            "#A5D6A7",
            FONT_R,
            (100, 455),
        ),
        ("", 10, "white", FONT_R, (100, 475)),
        (
            "Self-attention w encoderze: cechy obrazu 'rozmawiają' ze sobą",
            15,
            "#64B5F6",
            FONT_R,
            (80, 500),
        ),
        (
            "Cross-attention w decoderze: queries 'pytają' cechy obrazu",
            15,
            "#CE93D8",
            FONT_R,
            (80, 535),
        ),
        (
            "→ query 'rozumie' który fragment obrazu to 'jego' obiekt",
            15,
            "#FFE082",
            FONT_R,
            (80, 570),
        ),
        (
            "DETR = Detekcja Eliminująca Trikowe Redundancje (NMS, anchory)",
            16,
            "#FFE082",
            FONT_R,
            (80, 620),
        ),
        (
            "Wada: wolniejszy trening (O(n²) attention) | Zaleta: prostszy pipeline!",
            15,
            "#78909C",
            FONT_R,
            (80, 660),
        ),
    ]
    slides.append(_text_slide(detr_details, duration=STEP_DUR + 1))

    # Slide 3: Two-stage vs One-stage vs Transformer summary
    summary_lines = [
        (
            "Podsumowanie: Two-stage vs One-stage vs Transformer",
            22,
            "#FFE082",
            FONT_B,
            (80, 30),
        ),
        ("", 10, "white", FONT_R, (80, 55)),
        ("TWO-STAGE (R-CNN family):", 18, "#EF9A9A", FONT_B, (80, 90)),
        (
            "  (1) Generuj propozycje → (2) Klasyfikuj per region",
            15,
            "white",
            FONT_R,
            (100, 125),
        ),
        (
            "  + Wysoka precyzja | - Wolniejsze (2 przejścia)",
            15,
            "#78909C",
            FONT_R,
            (100, 155),
        ),
        (
            "  R-CNN → Fast R-CNN → Faster R-CNN (0.2s)",
            15,
            "#B0BEC5",
            FONT_R,
            (100, 185),
        ),
        ("", 10, "white", FONT_R, (80, 210)),
        ("ONE-STAGE (YOLO, SSD):", 18, "#A5D6A7", FONT_B, (80, 240)),
        (
            "  Siatka → predykcja all-in-one (1 przejście)",
            15,
            "white",
            FONT_R,
            (100, 275),
        ),
        (
            "  + Bardzo szybkie (45-155 fps) | - Historycznie mniej precyzyjne",
            15,
            "#78909C",
            FONT_R,
            (100, 305),
        ),
        (
            "  YOLOv8 (2023): anchor-free, dorównuje two-stage!",
            15,
            "#B0BEC5",
            FONT_R,
            (100, 335),
        ),
        ("", 10, "white", FONT_R, (80, 360)),
        ("TRANSFORMER (DETR):", 18, "#CE93D8", FONT_B, (80, 390)),
        (
            "  Object queries + self-attention (globalny kontekst)",
            15,
            "white",
            FONT_R,
            (100, 425),
        ),
        (
            "  + Brak NMS/anchorów | - Wolniejszy trening (O(n²))",
            15,
            "#78909C",
            FONT_R,
            (100, 455),
        ),
        (
            "  Hungarian matching → 1:1 obiekt↔predykcja → brak duplikatów",
            15,
            "#B0BEC5",
            FONT_R,
            (100, 485),
        ),
        ("", 10, "white", FONT_R, (80, 510)),
        (
            "Trend: coraz prostsze pipeline, mniej ręcznych komponentów",
            17,
            "white",
            FONT_R,
            (80, 540),
        ),
        (
            "  R-CNN (SS+CNN+SVM+NMS) → YOLO (backbone+head+NMS) → DETR (backbone+transformer)",
            14,
            "#90CAF9",
            FONT_R,
            (80, 580),
        ),
        (
            "Metryki: mAP@0.5 (standard), mAP@0.5:0.95 (surowsza), IoU do dopasowania",
            15,
            "#78909C",
            FONT_R,
            (80, 630),
        ),
    ]
    slides.append(_text_slide(summary_lines, duration=STEP_DUR + 1))

    return slides


# ── NMS + IoU ─────────────────────────────────────────────────────
def _nms_iou_demo() -> list[CompositeVideoClip]:
    """Animate NMS and IoU concepts."""
    slides = []

    def make_nms_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        progress = min(t / (STEP_DUR * 0.7), 1.0)

        # Draw overlapping bounding boxes
        ox, oy = 100, 200
        obj_w, obj_h = 150, 120

        # Multiple overlapping detections for same object
        boxes = [
            (ox, oy, obj_w, obj_h, 0.95, (255, 80, 80)),  # best
            (ox + 15, oy - 10, obj_w + 10, obj_h + 5, 0.90, (200, 60, 60)),
            (ox - 10, oy + 5, obj_w - 5, obj_h + 10, 0.85, (160, 50, 50)),
        ]
        # Different object far away
        boxes.append((ox + 350, oy + 50, 100, 100, 0.40, (80, 180, 255)))

        for i, (bx, by, bw, bh, _conf, color) in enumerate(boxes):
            if progress > 0.4 and i > 0 and i < 3:
                # After NMS, these get removed (shown as faded/crossed)
                color = (60, 40, 40)

            for tt in range(2):
                frame[by - tt : by + bh + tt, bx - tt : bx - tt + 2] = color
                frame[by - tt : by + bh + tt, bx + bw + tt - 2 : bx + bw + tt] = color
                frame[by - tt : by - tt + 2, bx - tt : bx + bw + tt] = color
                frame[by + bh + tt - 2 : by + bh + tt, bx - tt : bx + bw + tt] = color

        # IoU visualization on right side
        iou_x, iou_y = 700, 200
        # Box A
        frame[iou_y : iou_y + 100, iou_x : iou_x + 100] = (80, 80, 200)
        # Box B (overlapping)
        frame[iou_y + 40 : iou_y + 140, iou_x + 40 : iou_x + 140] = (200, 80, 80)
        # Intersection highlighted
        frame[iou_y + 40 : iou_y + 100, iou_x + 40 : iou_x + 100] = (200, 150, 200)

        return frame

    nms_clip = VideoClip(make_nms_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [nms_clip]
    labels = [
        ("NMS (Non-Maximum Suppression) + IoU", 28, "#FFE082", FONT_B, (80, 20)),
        (
            "NMS = Najlepszy Ma Się dobrze — zachowaj najlepszą, usuń duplikaty",
            18,
            "#B0BEC5",
            FONT_R,
            (80, 65),
        ),
        ("conf=0.95 ✓", 14, "#A5D6A7", FONT_B, (100, 340)),
        ("0.90 ✗ IoU>0.5", 13, "#EF9A9A", FONT_R, (100, 365)),
        ("0.85 ✗ IoU>0.5", 13, "#EF9A9A", FONT_R, (100, 390)),
        ("0.40 ✓ INNY obiekt", 13, "#64B5F6", FONT_R, (100, 420)),
        ("IoU = Intersection over Union", 18, "#FFE082", FONT_B, (700, 160)),
        ("IoU = pole(∩) / pole(AUB)", 16, "white", FONT_R, (700, 380)),
        ("Fioletowy = intersection", 14, "#CE93D8", FONT_R, (700, 410)),
        ("IoU > 0.5 → TEN SAM obiekt → usuń", 14, "#EF9A9A", FONT_R, (700, 440)),
        ("IoU < 0.5 → INNY obiekt → zachowaj", 14, "#A5D6A7", FONT_R, (700, 470)),
        (
            "DETR: jedyny detektor BEZ NMS (Hungarian matching zamiast tego)",
            14,
            "#78909C",
            FONT_R,
            (80, 620),
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


# ── Detector from Classifier ─────────────────────────────────────
def _detector_from_classifier() -> list[CompositeVideoClip]:
    """Show 3 approaches to building a detector from a classifier."""
    slides = []

    approaches = [
        (
            "Podejście 1: Sliding Window (NAJWOLNIEJSZE)",
            [
                ("Okno przesuwa się po obrazie w wielu skalach", "#B0BEC5"),
                ("Każde okno → klasyfikator (np. ResNet) → klasa + pewność", "#B0BEC5"),
                ("~18 000 okien x 10ms = ~3 minuty na obraz!", "#EF9A9A"),
                ("Mnemonik: WYCINAJ i PYTAJ — jak wycinanie ciasteczek", "#FFE082"),
            ],
            "SRF",
        ),
        (
            "Podejście 2: Region Proposals (= R-CNN)",
            [
                ("Selective Search → ~2000 inteligentnych regionów", "#B0BEC5"),
                ("Każdy region → CNN → wektor cech → SVM klasyfikuje", "#B0BEC5"),
                ("~2000 x 10ms = ~20 sec — 9x szybciej!", "#64B5F6"),
                (
                    "Mnemonik: INTELIGENTNE CIĘCIE — wytnij tylko tam gdzie wiśnie",
                    "#FFE082",
                ),
            ],
            "SRF",
        ),
        (
            "Podejście 3: Fine-tune backbone (NAJLEPSZE)",
            [
                (
                    "Pretrained backbone (ResNet) → odetnij FC → dodaj detection head",
                    "#B0BEC5",
                ),
                (
                    "Detection head = głowica klasyfikacji + głowica regresji bbox",
                    "#B0BEC5",
                ),
                ("~0.2 sec/obraz, najlepsza jakość (mAP ~42%)", "#A5D6A7"),
                ("Mnemonik: PRZESZCZEP GŁOWY — ten sam silnik, nowa głowa", "#FFE082"),
            ],
            "SRF",
        ),
    ]

    for title, points, _mnem in approaches:
        lines = [
            (title, 24, "#FFE082", FONT_B, (80, 140)),
        ]
        for i, (text, color) in enumerate(points):
            lines.append((f"• {text}", 18, color, FONT_R, (100, 220 + i * 50)))

        lines.append(
            (
                "Detektor z klasyfikatora: SRF = Sliding → Region → Fine-tune",
                16,
                "#78909C",
                FONT_R,
                (80, 520),
            )
        )
        lines.append(
            (
                "= Szukaj Ręcznie, Finalnie optymalizuj!",
                16,
                "#90CAF9",
                FONT_R,
                (80, 550),
            )
        )

        slides.append(_text_slide(lines, duration=STEP_DUR))

    return slides


def _text_slide(
    lines: list[tuple[str, int, str, str, tuple[str | int, str | int]]],
    duration: float = STEP_DUR,
) -> CompositeVideoClip:
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(duration)
    clips: list[VideoClip] = [bg]
    for text, font_size, color, font, pos in lines:
        tc = (
            _tc(
                text=text,
                font_size=font_size,
                color=color,
                font=font,
            )
            .with_duration(duration)
            .with_position(pos)
        )
        clips.append(tc)
    return CompositeVideoClip(clips, size=(W, H)).with_effects(
        [FadeIn(0.3), FadeOut(0.3)]
    )


# ── Methods comparison ────────────────────────────────────────────
def _methods_comparison() -> CompositeVideoClip:
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(10.0)
    title = (
        _tc(
            text="Porównanie detektorów",
            font_size=36,
            color="white",
            font=FONT_B,
        )
        .with_duration(10.0)
        .with_position(("center", 20))
    )

    rows = [
        ("Model", "Rok", "Typ", "Szybkość", "Kluczowe"),
        ("HOG+SVM", "2005", "Klasyczny", "~1 fps", "Gradient histogramy"),
        ("Viola-Jones", "2001", "Klasyczny", "30+ fps", "Haar+Cascade"),
        ("R-CNN", "2014", "Two-stage", "50 sec!", "CNN per region"),
        ("Fast R-CNN", "2015", "Two-stage", "2 sec", "ROI Pooling"),
        ("Faster R-CNN", "2015", "Two-stage", "5 fps", "RPN w sieci"),
        ("YOLO", "2016", "One-stage", "45+ fps", "Siatka SxS"),
        ("DETR", "2020", "Transformer", "~40 fps", "Bez NMS!"),
    ]

    clips: list[VideoClip] = [bg, title]
    for i, row in enumerate(rows):
        y_pos = 75 + i * 72
        col_x = [40, 200, 280, 400, 530]
        for j, cell in enumerate(row):
            fs = 16 if i > 0 else 18
            color = "#64B5F6" if i == 0 else "#E0E0E0"
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


# ── Main ──────────────────────────────────────────────────────────
def main() -> None:
    """Generate the Q24 object detection visualization video."""
    sections: list[VideoClip] = []

    sections.append(
        _make_header(
            "Pytanie 24: Detekcja obiektów",
            "Problem, metody klasyczne, deep learning",
            duration=4.0,
        )
    )

    # What is detection
    sections.append(
        _make_header("Co to detekcja?", "Lokalizacja (bbox) + klasyfikacja (klasa)")
    )
    sections.extend(_detection_concept())

    # HOG + SVM
    sections.append(
        _make_header("HOG + SVM (2005)", "Klasyczny pipeline — gradient histogramy")
    )
    sections.extend(_hog_svm_demo())

    # Viola-Jones
    sections.append(
        _make_header("Viola-Jones (2001)", "Haar features + Integral Image + Cascade")
    )
    sections.extend(_viola_jones_demo())

    # R-CNN evolution (overview)
    sections.append(_make_header("Ewolucja R-CNN", "R-CNN → Fast R-CNN → Faster R-CNN"))
    sections.extend(_rcnn_evolution())

    # R-CNN detailed pipeline
    sections.append(
        _make_header("R-CNN: krok po kroku", "Selective Search → 2000xCNN → SVM → NMS")
    )
    sections.extend(_rcnn_detailed())

    # ROI Pooling
    sections.append(
        _make_header("ROI Pooling (Fast R-CNN)", "CNN raz + ROI Pool → 25x szybciej")
    )
    sections.extend(_roi_pooling_demo())

    # RPN + Anchors
    sections.append(
        _make_header("RPN + Anchor Boxes", "Faster R-CNN: propozycje W SIECI")
    )
    sections.extend(_rpn_anchors_demo())

    # YOLO
    sections.append(
        _make_header("YOLO (2016)", "You Only Look Once — jednoetapowy detektor")
    )
    sections.extend(_yolo_demo())

    # YOLO architecture detail
    sections.append(
        _make_header("YOLO: Architektura", "Backbone → Neck → Head → tensor SxS")
    )
    sections.extend(_yolo_architecture())

    # DETR
    sections.append(_make_header("DETR (2020)", "Transformer: bez NMS, bez anchorów!"))
    sections.extend(_detr_demo())

    # NMS + IoU
    sections.append(_make_header("NMS + IoU", "Post-processing — usuwanie duplikatów"))
    sections.extend(_nms_iou_demo())

    # Detector from classifier
    sections.append(
        _make_header(
            "Detektor z klasyfikatora", "3 podejścia: Sliding → Region → Fine-tune"
        )
    )
    sections.extend(_detector_from_classifier())

    # Comparison table
    sections.append(_methods_comparison())

    # Summary
    sections.append(
        _make_header(
            "Podsumowanie",
            "Klasyczne: HOG+SVM, Viola-Jones | DL: R-CNN, YOLO, DETR",
            duration=4.0,
        )
    )

    final = concatenate_videoclips(sections, method="compose")
    final.write_videofile(
        OUTPUT, fps=FPS, codec="libx264", audio=False, preset="medium", threads=4
    )
    print(f"Video saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
