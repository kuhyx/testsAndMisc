"""MoviePy visualization for PYTANIE 2: Shortest path algorithms.

Creates an animated video walking through Dijkstra, Bellman-Ford, and A*
on a small example graph, rendering each algorithm step by step.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
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
STEP_DUR = 8.0
HEADER_DUR = 5.0
FONT_B = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/TTF/DejaVuSans.ttf"
OUTPUT_DIR = Path(__file__).resolve().parent / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = str(OUTPUT_DIR / "q02_shortest_path.mp4")

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Graph definition
NODE_POS = {"S": (250, 280), "A": (550, 180), "B": (550, 450), "C": (850, 320)}
EDGES_DIJKSTRA = [
    ("S", "A", 2),
    ("S", "B", 5),
    ("A", "C", 3),
    ("B", "A", 1),
    ("B", "C", 6),
]
EDGES_BF = [("S", "A", 2), ("A", "C", 3), ("S", "B", 5), ("B", "A", -4)]

# Colors
BG = (20, 20, 40)
COL_DEFAULT = (70, 130, 200)
COL_CURRENT = (255, 200, 50)
COL_VISITED = (80, 200, 100)
COL_EDGE = (100, 100, 130)
COL_EDGE_ACT = (255, 100, 80)
INF = "inf"


def _tc(**kwargs: object) -> TextClip:
    """TextClip wrapper that adds enough bottom margin to prevent clipping."""
    fs = kwargs.get("font_size", 24)
    m = int(fs) // 3 + 2
    kwargs["margin"] = (0, m)
    return TextClip(**kwargs)


def _make_header(
    title: str, subtitle: str, duration: float = HEADER_DUR
) -> CompositeVideoClip:
    bg = ColorClip(size=(W, H), color=BG).with_duration(duration)
    t = (
        _tc(
            text=title,
            font_size=52,
            color="white",
            font=FONT_B,
        )
        .with_duration(duration)
        .with_position(("center", 250))
    )
    s = (
        _tc(
            text=subtitle,
            font_size=28,
            color="#AABBCC",
            font=FONT_R,
        )
        .with_duration(duration)
        .with_position(("center", 340))
    )
    return CompositeVideoClip([bg, t, s], size=(W, H)).with_effects(
        [FadeIn(0.5), FadeOut(0.5)]
    )


def _draw_circle(
    frame: np.ndarray, cx: int, cy: int, r: int, color: tuple[int, ...]
) -> None:
    yy, xx = np.ogrid[:H, :W]
    mask = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r**2
    frame[mask] = color


def _draw_line(
    frame: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, ...],
    thickness: int = 2,
) -> None:
    x1, y1 = start
    x2, y2 = end
    length = max(int(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)), 1)
    for i in range(length):
        frac = i / length
        px = int(x1 + frac * (x2 - x1))
        py = int(y1 + frac * (y2 - y1))
        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                nx, ny = px + dx, py + dy
                if 0 <= nx < W and 0 <= ny < H:
                    frame[ny, nx] = color


def _draw_arrow(
    frame: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, ...],
    thickness: int = 2,
) -> None:
    x1, y1 = start
    x2, y2 = end
    r = 32
    length = max(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 1)
    ddx = (x2 - x1) / length
    ddy = (y2 - y1) / length
    sx = int(x1 + ddx * r)
    sy = int(y1 + ddy * r)
    ex = int(x2 - ddx * r)
    ey = int(y2 - ddy * r)
    _draw_line(frame, (sx, sy), (ex, ey), color, thickness)
    angle = np.arctan2(ey - sy, ex - sx)
    arrow_len = 12
    for side in [-1, 1]:
        a = angle + np.pi + side * 0.4
        ax = int(ex + arrow_len * np.cos(a))
        ay = int(ey + arrow_len * np.sin(a))
        _draw_line(frame, (ex, ey), (ax, ay), color, thickness)


def _render_graph(
    nodes: dict[str, tuple[int, int]],
    edges: list[tuple[str, str, int]],
    _distances: dict[str, str],
    current: str | None = None,
    visited: set[str] | None = None,
    active_edge: tuple[str, str] | None = None,
) -> np.ndarray:
    if visited is None:
        visited = set()
    frame = np.full((H, W, 3), BG, dtype=np.uint8)

    for src, dst, _w in edges:
        sx, sy = nodes[src]
        dx, dy = nodes[dst]
        ec = COL_EDGE_ACT if active_edge == (src, dst) else COL_EDGE
        _draw_arrow(frame, (sx, sy), (dx, dy), ec, thickness=2)

    for name, (x, y) in nodes.items():
        if name == current:
            nc = COL_CURRENT
        elif name in visited:
            nc = COL_VISITED
        else:
            nc = COL_DEFAULT
        _draw_circle(frame, x, y, 30, nc)
        # Border ring
        border = tuple(max(c - 40, 0) for c in nc)
        yy, xx = np.ogrid[:H, :W]
        ring = (((xx - x) ** 2 + (yy - y) ** 2) <= 30**2) & (
            ((xx - x) ** 2 + (yy - y) ** 2) > 27**2
        )
        frame[ring] = border

    return frame


@dataclass
class _StepConfig:
    """Configuration for a single algorithm visualization step."""

    nodes: dict[str, tuple[int, int]]
    edges: list[tuple[str, str, int]]
    distances: dict[str, str]
    current: str | None = None
    visited: set[str] | None = None
    active_edge: tuple[str, str] | None = None
    step_text: str = ""
    algo_name: str = ""


def _make_step(
    cfg: _StepConfig,
    duration: float = STEP_DUR,
) -> CompositeVideoClip:
    nodes = cfg.nodes
    edges = cfg.edges
    distances = cfg.distances
    current = cfg.current
    visited = cfg.visited if cfg.visited is not None else set()
    active_edge = cfg.active_edge
    step_text = cfg.step_text
    algo_name = cfg.algo_name

    graph_frame = _render_graph(nodes, edges, distances, current, visited, active_edge)

    def make_frame(_t: float) -> np.ndarray:
        return graph_frame.copy()

    bg_clip = VideoClip(make_frame, duration=duration).with_fps(FPS)
    overlays: list[VideoClip] = [bg_clip]

    if algo_name:
        overlays.append(
            _tc(
                text=algo_name,
                font_size=28,
                color="#64B5F6",
                font=FONT_B,
            )
            .with_duration(duration)
            .with_position((40, 20))
        )

    dist_items = [f"{k}: {v}" for k, v in distances.items()]
    table_text = "dist = { " + ",  ".join(dist_items) + " }"
    overlays.append(
        _tc(
            text=table_text,
            font_size=18,
            color="#B0BEC5",
            font=FONT_R,
        )
        .with_duration(duration)
        .with_position((40, 60))
    )

    visited_text = f"visited = {{ {', '.join(sorted(visited))} }}"
    overlays.append(
        _tc(
            text=visited_text,
            font_size=18,
            color="#A5D6A7",
            font=FONT_R,
        )
        .with_duration(duration)
        .with_position((40, 90))
    )

    for src, dst, w in edges:
        sx, sy = nodes[src]
        dx, dy = nodes[dst]
        mx = (sx + dx) // 2 - 6
        my = (sy + dy) // 2 - 12
        wcol = "#FF8A65" if active_edge == (src, dst) else "#90A4AE"
        overlays.append(
            _tc(
                text=str(w),
                font_size=16,
                color=wcol,
                font=FONT_B,
            )
            .with_duration(duration)
            .with_position((mx, my))
        )

    for name, (x, y) in nodes.items():
        overlays.append(
            _tc(
                text=name,
                font_size=20,
                color="white",
                font=FONT_B,
            )
            .with_duration(duration)
            .with_position((x - 7, y - 12))
        )
        d = distances.get(name, INF)
        overlays.append(
            _tc(
                text=f"d={d}",
                font_size=14,
                color="#FFE082",
                font=FONT_R,
            )
            .with_duration(duration)
            .with_position((x - 16, y + 35))
        )

    if step_text:
        overlays.append(
            _tc(
                text=step_text,
                font_size=18,
                color="#E0E0E0",
                font=FONT_R,
            )
            .with_duration(duration)
            .with_position((40, 600))
        )

    return CompositeVideoClip(overlays, size=(W, H)).with_effects(
        [FadeIn(0.3), FadeOut(0.3)]
    )


def main() -> None:
    """Generate the Q02 shortest path visualization video."""
    from python_pkg.praca_magisterska_video._q02_algorithm_steps import (
        _astar_steps,
        _bellman_ford_steps,
        _comparison_slide,
        _dijkstra_steps,
    )

    sections: list[VideoClip] = []

    sections.append(
        _make_header(
            "Pytanie 2: Algorytmy najkrótszej ścieżki",
            "Dijkstra * Bellman-Ford * A*",
            duration=8.0,
        )
    )

    sections.append(_make_header("Algorytm Dijkstry", "Zachłanny, SSSP, wagi ≥ 0"))
    sections.extend(_dijkstra_steps())

    sections.append(
        _make_header("Algorytm Bellmana-Forda", "Prog. dynamiczne, ujemne wagi, O(V·E)")
    )
    sections.extend(_bellman_ford_steps())

    sections.append(
        _make_header("Algorytm A*", "Heurystyczny, f(n)=g(n)+h(n), Single-pair")
    )
    sections.extend(_astar_steps())

    sections.append(_comparison_slide())

    sections.append(
        _make_header(
            "Podsumowanie",
            "Dijkstra=chciwy | Bellman-Ford=brute force x(V-1) | A*=Dijkstra+GPS",
            duration=8.0,
        )
    )

    final = concatenate_videoclips(sections, method="compose")
    final.write_videofile(
        OUTPUT, fps=FPS, codec="libx264", audio=False, preset="medium", threads=4
    )
    _logger.info("Video saved to: %s", OUTPUT)


if __name__ == "__main__":
    main()
