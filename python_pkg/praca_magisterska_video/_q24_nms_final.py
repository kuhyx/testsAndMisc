"""NMS/IoU, detector-from-classifier, and methods comparison."""

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
from moviepy import ColorClip, CompositeVideoClip, VideoClip
from moviepy.video.fx import FadeIn, FadeOut
import numpy as np


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
            dc = color
            nms_phase = 0.4
            nms_limit = 3
            if progress > nms_phase and i > 0 and i < nms_limit:
                # After NMS, these get removed (shown as faded/crossed)
                dc = (60, 40, 40)

            for tt in range(2):
                frame[by - tt : by + bh + tt, bx - tt : bx - tt + 2] = dc
                frame[by - tt : by + bh + tt, bx + bw + tt - 2 : bx + bw + tt] = dc
                frame[by - tt : by - tt + 2, bx - tt : bx + bw + tt] = dc
                frame[by + bh + tt - 2 : by + bh + tt, bx - tt : bx + bw + tt] = dc

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


# ── Methods comparison ────────────────────────────────────────────
def _methods_comparison() -> CompositeVideoClip:
    """Create a comparison table of all detection methods."""
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
