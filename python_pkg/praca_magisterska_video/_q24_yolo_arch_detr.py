"""YOLO architecture detail and DETR transformer detection."""

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
                arrow_limit = 4
                if i < arrow_limit:
                    ax = bx + bw + 5
                    ay = by + bh // 2
                    frame[ay - 1 : ay + 2, ax : ax + 25] = (150, 150, 170)

        # Output tensor breakdown (right side)
        tensor_phase = 0.6
        if progress > tensor_phase:
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
            frame[gy + gc : gy + 2 * gc - 1, gx + gc : gx + 2 * gc - 1] = (
                80,
                200,
                120,
            )

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
                arrow_limit = 4
                if i < arrow_limit:
                    ax = bx + bw + 5
                    ay = by + bh // 2
                    frame[ay - 1 : ay + 2, ax : ax + 25] = (150, 150, 170)

        # Object queries illustration (right side)
        query_phase = 0.5
        if progress > query_phase:
            qx, qy = 800, 140
            for i in range(6):
                y = qy + i * 50
                w = 130
                active_limit = 3
                active = i < active_limit
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
        (
            "  1. Sieć daje N=100 predykcji (queries)",
            15,
            "#64B5F6",
            FONT_R,
            (100, 220),
        ),
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
            "  R-CNN (SS+CNN+SVM+NMS) → YOLO "
            "(backbone+head+NMS) → DETR (backbone+transformer)",
            14,
            "#90CAF9",
            FONT_R,
            (80, 580),
        ),
        (
            "Metryki: mAP@0.5 (standard), mAP@0.5:0.95 (surowsza), "
            "IoU do dopasowania",
            15,
            "#78909C",
            FONT_R,
            (80, 630),
        ),
    ]
    slides.append(_text_slide(summary_lines, duration=STEP_DUR + 1))

    return slides
