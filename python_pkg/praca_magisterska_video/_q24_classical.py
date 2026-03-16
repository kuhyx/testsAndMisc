"""Classical detection methods: detection concept, HOG+SVM, Viola-Jones."""

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
        gradient_phase = 0.2
        if progress > gradient_phase:
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
            "Haar: kontrast jasna/ciemna | Integral Image: "
            "suma prostokąta O(1) = 4 odczyty",
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
