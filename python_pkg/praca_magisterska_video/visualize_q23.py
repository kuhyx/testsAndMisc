"""MoviePy visualization for PYTANIE 23: Image Segmentation.

Creates animated video demonstrating:
- What segmentation is (pixel-level classification)
- Thresholding / Otsu (bimodal histogram)
- Region Growing (BFS flood fill)
- Watershed (topographic flooding)
- U-Net encoder-decoder architecture
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
OUTPUT = str(OUTPUT_DIR / "q23_segmentation.mp4")

BG_COLOR = (15, 20, 35)
rng = np.random.default_rng(42)


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


def _text_slide(
    lines: list[tuple[str, int, str, str, tuple[str | int, str | int]]],
    duration: float = STEP_DUR,
) -> CompositeVideoClip:
    """Create a slide with multiple text elements."""
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


# ── Segmentation concept ─────────────────────────────────────────
def _segmentation_concept() -> list[CompositeVideoClip]:
    """Show what segmentation is: pixel-level labeling."""
    slides = []

    # Synthetic image: grid of colored pixels
    def make_image_frame(_t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        # Draw a small "image" grid
        grid_x, grid_y = 100, 150
        cell = 40
        # Sky (top rows)
        colors_map = [
            [(135, 206, 235)] * 8,  # sky
            [(135, 206, 235)] * 5 + [(34, 139, 34)] * 3,  # sky + tree
            [(34, 139, 34)] * 3
            + [(128, 128, 128)] * 3
            + [(34, 139, 34)] * 2,  # tree+road+tree
            [(128, 128, 128)] * 3
            + [(200, 50, 50)] * 2
            + [(128, 128, 128)] * 3,  # road+car+road
        ]
        labels_map = [
            ["niebo"] * 8,
            ["niebo"] * 5 + ["drzewo"] * 3,
            ["drzewo"] * 3 + ["droga"] * 3 + ["drzewo"] * 2,
            ["droga"] * 3 + ["samochód"] * 2 + ["droga"] * 3,
        ]
        label_colors = {
            "niebo": (100, 180, 255),
            "drzewo": (50, 200, 50),
            "droga": (180, 180, 180),
            "samochód": (255, 80, 80),
        }

        for r, row in enumerate(colors_map):
            for c, col in enumerate(row):
                y = grid_y + r * cell
                x = grid_x + c * cell
                frame[y : y + cell - 2, x : x + cell - 2] = col

        # Draw segmentation map on the right
        seg_x = 600
        for r, row in enumerate(labels_map):
            for c, lab in enumerate(row):
                y = grid_y + r * cell
                x = seg_x + c * cell
                frame[y : y + cell - 2, x : x + cell - 2] = label_colors[lab]

        return frame

    image_clip = VideoClip(make_image_frame, duration=STEP_DUR).with_fps(FPS)
    labels_text = [
        ("Obraz wejściowy", 22, "white", FONT_B, (170, 100)),
        ("Mapa segmentacji", 22, "white", FONT_B, (660, 100)),
        ("→", 50, "#FFE082", FONT_B, (450, 250)),
        ("Każdy piksel → etykieta klasy", 20, "#B0BEC5", FONT_R, (100, 420)),
        ("niebo  |  drzewo  |  droga  |  samochód", 18, "#90CAF9", FONT_R, (600, 420)),
        ("Segmentacja = klasyfikacja per-piksel", 24, "#FFE082", FONT_B, (100, 500)),
        (
            "Semantic: klasy bez instancji | Instance: rozróżnia obiekty | Panoptic: oba",
            16,
            "#78909C",
            FONT_R,
            (100, 560),
        ),
    ]
    clips: list[VideoClip] = [image_clip]
    for text, fs, color, font, pos in labels_text:
        tc = (
            _tc(text=text, font_size=fs, color=color, font=font)
            .with_duration(STEP_DUR)
            .with_position(pos)
        )
        clips.append(tc)

    slides.append(
        CompositeVideoClip(clips, size=(W, H)).with_effects([FadeIn(0.3), FadeOut(0.3)])
    )
    return slides


# ── Thresholding / Otsu ───────────────────────────────────────────
def _thresholding_demo() -> list[CompositeVideoClip]:
    """Animate thresholding and Otsu concept."""
    slides = []

    # Show histogram & threshold
    def make_threshold_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        # Draw bimodal histogram bars
        bar_start_x = 80
        bar_y = 500
        bar_w = 4

        for i in range(256):
            # Bimodal: peaks at 60 and 190
            h1 = 200 * np.exp(-((i - 60) ** 2) / (2 * 20**2))
            h2 = 150 * np.exp(-((i - 190) ** 2) / (2 * 25**2))
            bar_h = int(h1 + h2)
            x = bar_start_x + i * bar_w
            if x + bar_w < W:
                frame[bar_y - bar_h : bar_y, x : x + bar_w - 1] = (150, 150, 170)

        # Animated threshold line
        threshold = int(60 + (190 - 60) * min(t / (STEP_DUR * 0.7), 1.0))
        tx = bar_start_x + threshold * bar_w
        if tx < W:
            frame[bar_y - 250 : bar_y + 10, tx : tx + 3] = (255, 80, 80)

        # Color the two sides
        for i in range(threshold):
            x = bar_start_x + i * bar_w
            h1 = 200 * np.exp(-((i - 60) ** 2) / (2 * 20**2))
            h2 = 150 * np.exp(-((i - 190) ** 2) / (2 * 25**2))
            bar_h = int(h1 + h2)
            if x + bar_w < W and bar_h > 0:
                frame[bar_y - bar_h : bar_y, x : x + bar_w - 1] = (70, 130, 200)

        for i in range(threshold, 256):
            x = bar_start_x + i * bar_w
            h1 = 200 * np.exp(-((i - 60) ** 2) / (2 * 20**2))
            h2 = 150 * np.exp(-((i - 190) ** 2) / (2 * 25**2))
            bar_h = int(h1 + h2)
            if x + bar_w < W and bar_h > 0:
                frame[bar_y - bar_h : bar_y, x : x + bar_w - 1] = (200, 100, 80)

        return frame

    hist_clip = VideoClip(make_threshold_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [hist_clip]
    labels = [
        ("Progowanie (Thresholding) z metodą Otsu", 28, "#FFE082", FONT_B, (80, 30)),
        (
            "Histogram jasności pikseli — dwumodalny (bimodal)",
            20,
            "#B0BEC5",
            FONT_R,
            (80, 80),
        ),
        ("Garb 1: piksele obiektu (ciemne ~60)", 16, "#64B5F6", FONT_R, (80, 120)),
        ("Garb 2: piksele tła (jasne ~190)", 16, "#EF9A9A", FONT_R, (80, 150)),
        (
            "Próg T (czerwona linia) dzieli piksele na 2 klasy",
            18,
            "white",
            FONT_R,
            (80, 540),
        ),
        (
            "Otsu: automatycznie testuje T=0..255, minimalizuje σ² wewnątrzklasową",
            16,
            "#A5D6A7",
            FONT_R,
            (80, 580),
        ),
        (
            "Piksel ≤ T → klasa 0 (tło) | Piksel > T → klasa 1 (obiekt)",
            16,
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


# ── Region Growing ────────────────────────────────────────────────
def _region_growing_demo() -> list[CompositeVideoClip]:
    """Animate region growing BFS from a seed pixel."""
    slides = []

    grid_size = 10
    cell_size = 40
    rng = np.random.default_rng(42)
    # Create a simple grid: dark region (30-80) and bright region (160-220)
    grid = np.zeros((grid_size, grid_size), dtype=np.uint8)
    grid[:] = 60  # dark background
    grid[2:7, 3:8] = 180  # bright rectangle

    # Add some noise
    noise = rng.integers(-15, 15, (grid_size, grid_size))
    grid = np.clip(grid.astype(int) + noise, 0, 255).astype(np.uint8)

    # BFS steps from seed (4, 5)
    seed = (4, 5)
    threshold_val = 50
    visited_order: list[tuple[int, int]] = []
    queue = [seed]
    visited_set = {seed}
    while queue:
        r, c = queue.pop(0)
        visited_order.append((r, c))
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if (
                0 <= nr < grid_size
                and 0 <= nc < grid_size
                and (nr, nc) not in visited_set
            ) and abs(int(grid[nr, nc]) - int(grid[seed])) < threshold_val:
                visited_set.add((nr, nc))
                queue.append((nr, nc))

    def make_region_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        ox, oy = 100, 180

        # How many cells to show as visited
        progress = min(t / (STEP_DUR * 0.8), 1.0)
        n_visited = int(progress * len(visited_order))

        for r in range(grid_size):
            for c in range(grid_size):
                x = ox + c * cell_size
                y = oy + r * cell_size
                val = grid[r, c]
                color = (val, val, val)

                # Highlight visited
                if (r, c) in visited_order[:n_visited]:
                    color = (80, 200, 120)  # green for region
                elif (r, c) == seed:
                    color = (255, 200, 50)  # yellow seed

                frame[y : y + cell_size - 2, x : x + cell_size - 2] = color

                # Show value
                # (drawn as a simple marker since we can't render text in numpy easily)

        # Mark the seed with a bright border
        sx = ox + seed[1] * cell_size
        sy = ox + seed[0] * cell_size + 80
        frame[sy : sy + cell_size, sx : sx + 2] = (255, 200, 50)
        frame[sy : sy + cell_size, sx + cell_size - 2 : sx + cell_size] = (255, 200, 50)
        frame[sy : sy + 2, sx : sx + cell_size] = (255, 200, 50)
        frame[sy + cell_size - 2 : sy + cell_size, sx : sx + cell_size] = (255, 200, 50)

        return frame

    region_clip = VideoClip(make_region_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [region_clip]
    labels = [
        ("Region Growing — rozrastanie regionu", 28, "#FFE082", FONT_B, (100, 30)),
        ("Seed (ziarno) → BFS do podobnych sąsiadów", 20, "#B0BEC5", FONT_R, (100, 80)),
        (
            "Żółty = seed | Zielony = region | Szary = nieodwiedzone",
            16,
            "#78909C",
            FONT_R,
            (100, 120),
        ),
        (
            "Sąsiad PODOBNY (|jasność - jasność_regionu| < próg) → dodaj do regionu",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 600),
        ),
        (
            "Algorytm zatrzymuje się gdy brak podobnych sąsiadów",
            16,
            "#90CAF9",
            FONT_R,
            (100, 640),
        ),
        (
            "Mnemonik: PLAMA atramentu — rozlewa się na podobne piksele",
            18,
            "#EF9A9A",
            FONT_R,
            (100, 670),
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


# ── Watershed ─────────────────────────────────────────────────────
def _watershed_demo() -> list[CompositeVideoClip]:
    """Animate watershed flooding concept."""
    slides = []

    def make_watershed_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        # Draw terrain profile (1D cross-section)
        ox, oy = 100, 450
        terrain_w = 900
        terrain_points = 100

        xs = np.linspace(0, 1, terrain_points)
        # Two valleys with a ridge
        terrain = (
            120 * np.exp(-((xs - 0.25) ** 2) / 0.005)
            + 80 * np.exp(-((xs - 0.75) ** 2) / 0.008)
            + 30
        )
        terrain = 250 - terrain  # invert for visual (valleys at bottom)

        # Water level rises over time
        water_level = int(160 + 80 * min(t / (STEP_DUR * 0.7), 1.0))

        for i in range(terrain_points - 1):
            x1 = ox + int(xs[i] * terrain_w)
            x2 = ox + int(xs[i + 1] * terrain_w)
            y1 = oy - int(terrain[i])
            y2 = oy - int(terrain[i + 1])

            # Fill terrain
            for x in range(x1, min(x2 + 1, W)):
                top = min(y1, y2) - 5
                frame[top:oy, x : x + 1] = (100, 80, 60)

            # Fill water
            water_y = oy - water_level
            for x in range(x1, min(x2 + 1, W)):
                t_y = oy - int(terrain[i])
                if water_y < t_y:
                    # Water fills below terrain surface
                    fill_top = max(water_y, 0)
                    fill_bot = min(t_y, oy)
                    if fill_top < fill_bot:
                        frame[fill_top:fill_bot, x : x + 1] = (70, 130, 220)

        # Dam marker at ridge
        ridge_x = ox + int(0.5 * terrain_w)
        if water_level > 160:
            frame[oy - water_level : oy - 140, ridge_x - 2 : ridge_x + 2] = (
                255,
                80,
                80,
            )

        return frame

    ws_clip = VideoClip(make_watershed_frame, duration=STEP_DUR).with_fps(FPS)
    text_clips: list[VideoClip] = [ws_clip]
    labels = [
        ("Watershed — metoda zlewiska", 28, "#FFE082", FONT_B, (100, 20)),
        (
            "Obraz = mapa topograficzna (jasność = wysokość)",
            20,
            "#B0BEC5",
            FONT_R,
            (100, 65),
        ),
        (
            "Brązowy = teren (ciemne=doliny, jasne=szczyty)",
            16,
            "#8D6E63",
            FONT_R,
            (100, 100),
        ),
        ("Niebieski = woda zalewająca od minimów", 16, "#64B5F6", FONT_R, (100, 130)),
        (
            "Czerwony = TAMA (granica segmentu) — gdy woda z 2 dolin się spotka",
            16,
            "#EF9A9A",
            FONT_R,
            (100, 160),
        ),
        (
            "Problem: over-segmentation (za dużo regionów). Rozwiązanie: marker-controlled.",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 560),
        ),
        (
            "Mnemonik: ZALEWANIE terenu — granie gór = granice segmentów",
            18,
            "#FFE082",
            FONT_R,
            (100, 600),
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


# ── U-Net Architecture ───────────────────────────────────────────
def _unet_demo() -> list[CompositeVideoClip]:
    """Animate U-Net encoder-decoder architecture."""
    slides = []

    def make_unet_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR

        # Draw U-shape: encoder blocks going down, decoder going up
        # Encoder: 4 blocks getting smaller
        enc_sizes = [(80, 120), (60, 100), (45, 80), (30, 60)]
        dec_sizes = list(reversed(enc_sizes))
        enc_x = 150
        dec_x = 850

        progress = min(t / (STEP_DUR * 0.6), 1.0)
        n_blocks = int(progress * 8) + 1  # 1 to 8

        enc_positions = []
        y_offset = 120
        for i, (bw, bh) in enumerate(enc_sizes):
            x = enc_x
            y = y_offset + i * 130
            enc_positions.append((x, y, bw, bh))
            if i < n_blocks:
                # Draw encoder block
                frame[y : y + bh, x : x + bw] = (70, 130, 200)
                # Border
                frame[y : y + 2, x : x + bw] = (100, 180, 255)
                frame[y + bh - 2 : y + bh, x : x + bw] = (100, 180, 255)
                frame[y : y + bh, x : x + 2] = (100, 180, 255)
                frame[y : y + bh, x + bw - 2 : x + bw] = (100, 180, 255)

                # Down arrow
                if i < len(enc_sizes) - 1:
                    ax = x + bw // 2
                    ay = y + bh + 10
                    frame[ay : ay + 20, ax - 1 : ax + 2] = (150, 150, 170)

        # Bottleneck
        bx, by = 500, y_offset + 3 * 130 + 30
        if n_blocks > 4:
            frame[by : by + 50, bx : bx + 25] = (200, 100, 80)
            frame[by : by + 2, bx : bx + 25] = (255, 140, 100)
            frame[by + 48 : by + 50, bx : bx + 25] = (255, 140, 100)

        # Decoder
        dec_positions = []
        for i, (bw, bh) in enumerate(dec_sizes):
            x = dec_x
            y = y_offset + (3 - i) * 130
            dec_positions.append((x, y, bw, bh))
            if n_blocks > 4 + i + 1:
                frame[y : y + bh, x : x + bw] = (80, 200, 120)
                frame[y : y + 2, x : x + bw] = (120, 230, 150)
                frame[y + bh - 2 : y + bh, x : x + bw] = (120, 230, 150)
                frame[y : y + bh, x : x + 2] = (120, 230, 150)
                frame[y : y + bh, x + bw - 2 : x + bw] = (120, 230, 150)

                # Up arrow
                if i < len(dec_sizes) - 1:
                    ax = x + bw // 2
                    ay = y - 30
                    frame[ay : ay + 20, ax - 1 : ax + 2] = (150, 150, 170)

        # Skip connections (horizontal dashed lines)
        if n_blocks > 5:
            for i in range(min(n_blocks - 5, 4)):
                ey = enc_positions[i][1] + enc_positions[i][3] // 2
                ex_end = enc_positions[i][0] + enc_positions[i][2]
                dx_start = dec_x
                for dash_x in range(ex_end + 10, dx_start - 10, 15):
                    frame[ey : ey + 2, dash_x : dash_x + 8] = (255, 200, 50)

        return frame

    unet_clip = VideoClip(make_unet_frame, duration=STEP_DUR + 1).with_fps(FPS)
    text_clips: list[VideoClip] = [unet_clip]
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


# ── FCN Architecture ─────────────────────────────────────────────
def _fcn_demo() -> list[CompositeVideoClip]:
    """Animate FCN step-by-step: FC → Conv 1x1 transformation."""
    slides = []

    # Slide 1: Classic CNN vs FCN pipeline comparison
    def make_fcn_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.8), 1.0)

        # TOP: Classic CNN → FC → 1 label
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
        for i, ((bx, by), (bw, bh), color) in enumerate(blocks_classic):
            if i < n_top:
                frame[by : by + bh, bx : bx + bw] = color
                frame[by : by + 2, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                if i < 6:
                    ax = bx + bw + 3
                    ay = by + bh // 2
                    frame[ay - 1 : ay + 2, ax : ax + 12] = (150, 150, 170)

        # Red X over Flatten+FC when FCN appears
        if progress > 0.6:
            for d in range(-2, 3):
                for step in range(50):
                    x1 = 385 + int(step * 135 / 50)
                    y1 = top_y + step + d
                    if 0 <= y1 < H and 0 <= x1 < W:
                        frame[y1, x1] = (255, 80, 80)
                    y2 = top_y + 50 - step + d
                    if 0 <= y2 < H and 0 <= x1 < W:
                        frame[y2, x1] = (255, 80, 80)

        # BOTTOM: FCN pipeline
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
        if progress > 0.4:
            n_bot = min(int((progress - 0.4) / 0.6 * 7) + 1, 7)
            for i, ((bx, by), (bw, bh), color) in enumerate(blocks_fcn):
                if i < n_bot:
                    frame[by : by + bh, bx : bx + bw] = color
                    frame[by : by + 2, bx : bx + bw] = tuple(
                        min(c + 50, 255) for c in color
                    )
                    frame[by + bh - 2 : by + bh, bx : bx + bw] = tuple(
                        min(c + 50, 255) for c in color
                    )
                    if i < 6:
                        ax = bx + bw + 3
                        ay = by + bh // 2
                        frame[ay - 1 : ay + 2, ax : ax + 12] = (150, 150, 170)

        return frame

    fcn_clip = VideoClip(make_fcn_frame, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
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
    text_clips: list[VideoClip] = [fcn_clip]
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
            "Im więcej skip connections → tym więcej detali z encodera → ostrzejszy wynik",
            17,
            "white",
            FONT_R,
            (80, 620),
        ),
    ]
    slides.append(_text_slide(skip_lines, duration=STEP_DUR + 1))

    return slides


# ── DeepLab Architecture ─────────────────────────────────────────
def _deeplab_demo() -> list[CompositeVideoClip]:
    """Animate DeepLab: dilated convolution + ASPP step by step."""
    slides = []

    # Slide 1: Regular vs Dilated convolution
    def make_dilated_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.7), 1.0)

        cell = 36
        # Draw three grids side by side for rate=1, rate=2, rate=3
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
            # Draw background grid
            for r in range(grid_size):
                for c in range(grid_size):
                    x = gx + c * cell
                    y = gy + r * cell
                    frame[y : y + cell - 2, x : x + cell - 2] = (35, 40, 55)

            # Highlight filter positions
            for r, c in positions:
                x = gx + c * cell
                y = gy + r * cell
                frame[y : y + cell - 2, x : x + cell - 2] = (70, 130, 200)
                frame[y : y + 2, x : x + cell - 2] = (120, 180, 255)
                frame[y + cell - 4 : y + cell - 2, x : x + cell - 2] = (120, 180, 255)

        return frame

    dil_clip = VideoClip(make_dilated_frame, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
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
            "TE SAME 9 wag → WIĘKSZE pole widzenia → lepszy kontekst BEZ dodatkowych parametrów!",
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
    text_clips: list[VideoClip] = [dil_clip]
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

    # Slide 2: ASPP module step by step
    def make_aspp_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.7), 1.0)

        # Input feature map on left
        frame[250:330, 50:130] = (70, 130, 200)
        frame[250:252, 50:130] = (120, 180, 255)
        frame[328:330, 50:130] = (120, 180, 255)

        # ASPP parallel branches
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
                frame[by : by + 2, bx : bx + bw] = tuple(
                    min(c + 50, 255) for c in color
                )
                # Arrow from input
                ay = by + bh // 2
                frame[ay - 1 : ay + 2, 133:197] = (150, 150, 170)

        # Concatenation box
        if progress > 0.6:
            frame[250:530, 380:420] = (50, 60, 80)
            frame[250:252, 380:420] = (200, 200, 100)
            frame[528:530, 380:420] = (200, 200, 100)
            # Arrows from branches to concat
            for i, (_lbl, _h, (bx, by), (bw, bh), _c) in enumerate(branches):
                if i < n_branches:
                    ay = by + bh // 2
                    frame[ay - 1 : ay + 2, bx + bw + 3 : 378] = (150, 150, 170)

        # Final conv after concat
        if progress > 0.8:
            frame[350:420, 450:550] = (100, 200, 100)
            frame[350:352, 450:550] = (150, 230, 150)
            frame[418:420, 450:550] = (150, 230, 150)
            # Arrow from concat
            frame[388:391, 423:448] = (150, 150, 170)

        return frame

    aspp_clip = VideoClip(make_aspp_frame, duration=STEP_DUR + 1).with_fps(FPS)
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
    text_clips2: list[VideoClip] = [aspp_clip]
    for text, fs, color, font, pos in labels2:
        tc = (
            _tc(text=text, font_size=fs, color=color, font=font)
            .with_duration(dur)
            .with_position(pos)
        )
        text_clips2.append(tc)
    slides.append(
        CompositeVideoClip(text_clips2, size=(W, H)).with_effects(
            [FadeIn(0.3), FadeOut(0.3)]
        )
    )

    return slides


# ── Transformer Segmentation ────────────────────────────────────
def _transformer_seg_demo() -> list[CompositeVideoClip]:
    """Animate transformer-based segmentation: self-attention concept."""
    slides = []

    # Slide 1: CNN local vs Transformer global
    def make_attention_frame(t: float) -> np.ndarray:
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = BG_COLOR
        progress = min(t / (STEP_DUR * 0.7), 1.0)

        cell = 40
        grid_n = 6

        # LEFT: CNN — local receptive field
        lx, ly = 60, 200
        for r in range(grid_n):
            for c in range(grid_n):
                x = lx + c * cell
                y = ly + r * cell
                frame[y : y + cell - 2, x : x + cell - 2] = (35, 40, 55)

        # Highlight 3x3 kernel in CNN
        if progress > 0.2:
            cx, cy = 2, 2  # center cell
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    r, c = cy + dr, cx + dc
                    x = lx + c * cell
                    y = ly + r * cell
                    frame[y : y + cell - 2, x : x + cell - 2] = (70, 130, 200)
            # Center highlighted more
            x = lx + cx * cell
            y = ly + cy * cell
            frame[y : y + cell - 2, x : x + cell - 2] = (120, 180, 255)

        # RIGHT: Transformer — global attention
        rx, ry = 680, 200
        for r in range(grid_n):
            for c in range(grid_n):
                x = rx + c * cell
                y = ry + r * cell
                frame[y : y + cell - 2, x : x + cell - 2] = (35, 40, 55)

        # All cells connected to center
        if progress > 0.4:
            cx_t, cy_t = 2, 2
            # Center cell
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
                    # Color by "attention strength" — closer = stronger
                    dist = abs(r - cy_t) + abs(c - cx_t)
                    strength = max(30, 200 - dist * 30)
                    frame[y : y + cell - 2, x : x + cell - 2] = (
                        strength // 3,
                        strength // 2,
                        strength,
                    )
                    # Draw connection line
                    x1 = x + cell // 2
                    y1 = y + cell // 2
                    steps = max(abs(x1 - x0), abs(y1 - y0))
                    if steps > 0:
                        for s in range(0, steps, 3):
                            px = x0 + int((x1 - x0) * s / steps)
                            py = y0 + int((y1 - y0) * s / steps)
                            if 0 <= px < W - 1 and 0 <= py < H - 1:
                                frame[py : py + 1, px : px + 1] = (200, 180, 50)
                else:
                    continue
                break
            # Center highlighted strongly
            x = rx + cx_t * cell
            y = ry + cy_t * cell
            frame[y : y + cell - 2, x : x + cell - 2] = (255, 200, 50)

        return frame

    att_clip = VideoClip(make_attention_frame, duration=STEP_DUR + 1).with_fps(FPS)
    dur = STEP_DUR + 1
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
    text_clips: list[VideoClip] = [att_clip]
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
            "  2. Skalowanie: / √d (stabilność gradientów)",
            16,
            "white",
            FONT_R,
            (120, 355),
        ),
        (
            "  3. Softmax → wagi attention (sumują się do 1)",
            16,
            "white",
            FONT_R,
            (120, 390),
        ),
        (
            "  4. Mnożenie wag x V → ważona suma wartości",
            16,
            "white",
            FONT_R,
            (120, 425),
        ),
        (
            "Attention(Q,K,V) = softmax(Q · K\u1d40 / √d) · V",
            20,
            "#FFE082",
            FONT_B,
            (100, 480),
        ),
        (
            "Złożoność: O(n²) pamięci — n = liczba pikseli/tokenów",
            16,
            "#EF9A9A",
            FONT_R,
            (100, 535),
        ),
        (
            "Dlatego SegFormer używa efficient attention (liniowa złożoność)",
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
            "Mask2Former (2022): masked attention + unified (semantic+instance+panoptic)",
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
        ("Wspólna idea WSZYSTKICH sieci segmentacji:", 18, "#B0BEC5", FONT_R, (80, 90)),
        (
            "Encoder:  obraz → cechy (zmniejsza rozdzielczość, wyciąga CO)",
            16,
            "#64B5F6",
            FONT_R,
            (100, 140),
        ),
        (
            "Decoder:  cechy → mapa (zwiększa rozdzielczość, odtwarza GDZIE)",
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
            "FCN (2015):     Conv1x1 + skip → pierwsza end-to-end",
            16,
            "#64B5F6",
            FONT_R,
            (100, 275),
        ),
        (
            "U-Net (2015):   U-shape + skip concat → segmentacja medyczna",
            16,
            "#A5D6A7",
            FONT_R,
            (100, 310),
        ),
        (
            "DeepLab (2018): dilated conv + ASPP → multi-scale kontekst",
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
            "Ewolucja: więcej kontekstu + lepsze skip connections:",
            17,
            "white",
            FONT_R,
            (80, 465),
        ),
        (
            "  CNN lokal. → dilated (szersze RF) → transformer (global) → masked att.",
            16,
            "#B0BEC5",
            FONT_R,
            (80, 505),
        ),
        (
            "  addition skip → concat skip → cross-attention skip",
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
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(10.0)
    title = (
        _tc(
            text="Porównanie metod segmentacji",
            font_size=36,
            color="white",
            font=FONT_B,
        )
        .with_duration(10.0)
        .with_position(("center", 20))
    )

    rows = [
        ("Metoda", "Typ", "Idea", "Mnemonik"),
        ("Thresholding", "Klasyczna", "piksel > T → klasa 1", "PRÓG na bramce"),
        ("Otsu", "Klasyczna", "auto-próg, min σ²", "AUTO-bramkarz"),
        ("Region Growing", "Klasyczna", "BFS od seeda", "PLAMA atramentu"),
        ("Watershed", "Klasyczna", "zalewanie minimów", "ZALEWANIE terenu"),
        ("Mean Shift", "Klasyczna", "jądro → max gęstości", "KULKI do dołków"),
        ("U-Net", "Deep Learning", "encoder-decoder + skip", "Litera U + mosty"),
        ("DeepLab", "Deep Learning", "dilated conv + ASPP", "DZIURY w filtrze"),
    ]

    clips: list[VideoClip] = [bg, title]
    for i, row in enumerate(rows):
        y_pos = 75 + i * 72
        col_x = [40, 210, 340, 660]
        for j, cell in enumerate(row):
            fs = 16 if i > 0 else 18
            color = "#64B5F6" if i == 0 else ("#E0E0E0" if j < 3 else "#FFE082")
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
    """Generate the Q23 segmentation visualization video."""
    sections: list[VideoClip] = []

    sections.append(
        _make_header(
            "Pytanie 23: Segmentacja obrazu",
            "Problem, strategie klasyczne i sieci neuronowe",
            duration=4.0,
        )
    )

    # Concept
    sections.append(_make_header("Co to segmentacja?", "Etykieta klasy per piksel"))
    sections.extend(_segmentation_concept())

    # Thresholding
    sections.append(
        _make_header("Progowanie + Otsu", "Najprostsza metoda — automatyczny próg")
    )
    sections.extend(_thresholding_demo())

    # Region Growing
    sections.append(_make_header("Region Growing", "Seed → BFS do podobnych sąsiadów"))
    sections.extend(_region_growing_demo())

    # Watershed
    sections.append(_make_header("Watershed", "Obraz jako mapa topograficzna"))
    sections.extend(_watershed_demo())

    # FCN
    sections.append(
        _make_header("FCN (Deep Learning)", "Fully Convolutional Network — Conv 1x1")
    )
    sections.extend(_fcn_demo())

    # U-Net
    sections.append(
        _make_header(
            "U-Net (Deep Learning)", "Architektura encoder-decoder + skip concat"
        )
    )
    sections.extend(_unet_demo())

    # DeepLab
    sections.append(
        _make_header(
            "DeepLab v3+ (Deep Learning)", "Dilated convolution + ASPP — multi-scale"
        )
    )
    sections.extend(_deeplab_demo())

    # Transformer segmentation
    sections.append(
        _make_header(
            "Transformer (SegFormer, Mask2Former)", "Self-attention — globalny kontekst"
        )
    )
    sections.extend(_transformer_seg_demo())

    # Comparison
    sections.append(_methods_comparison())

    # Summary
    sections.append(
        _make_header(
            "Podsumowanie",
            "Klasyczne: próg/region/watershed | DL: FCN/U-Net/DeepLab/Transformer",
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
