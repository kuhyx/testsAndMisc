"""Classical segmentation methods: concept, thresholding, region growing, watershed."""

from __future__ import annotations

from moviepy import (
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
    _tc,
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
            "Semantic: klasy bez instancji | Instance: "
            "rozróżnia obiekty | Panoptic: oba",
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
        dam_visible_threshold = 160
        if water_level > dam_visible_threshold:
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
            "Problem: over-segmentation "
            "(za dużo regionów). "
            "Rozwiązanie: marker-controlled.",
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
