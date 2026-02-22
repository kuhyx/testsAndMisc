"""MoviePy visualization for PYTANIE 2: Shortest path algorithms.

Creates an animated video walking through Dijkstra, Bellman-Ford, and A*
on a small example graph, rendering each algorithm step by step.
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
STEP_DUR = 8.0
HEADER_DUR = 5.0
FONT_B = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/TTF/DejaVuSans.ttf"
OUTPUT_DIR = Path(__file__).resolve().parent / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = str(OUTPUT_DIR / "q02_shortest_path.mp4")

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
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, ...],
    thickness: int = 2,
) -> None:
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
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, ...],
    thickness: int = 2,
) -> None:
    r = 32
    length = max(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 1)
    ddx = (x2 - x1) / length
    ddy = (y2 - y1) / length
    sx = int(x1 + ddx * r)
    sy = int(y1 + ddy * r)
    ex = int(x2 - ddx * r)
    ey = int(y2 - ddy * r)
    _draw_line(frame, sx, sy, ex, ey, color, thickness)
    angle = np.arctan2(ey - sy, ex - sx)
    arrow_len = 12
    for side in [-1, 1]:
        a = angle + np.pi + side * 0.4
        ax = int(ex + arrow_len * np.cos(a))
        ay = int(ey + arrow_len * np.sin(a))
        _draw_line(frame, ex, ey, ax, ay, color, thickness)


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
        _draw_arrow(frame, sx, sy, dx, dy, ec, thickness=2)

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


def _make_step(
    nodes: dict[str, tuple[int, int]],
    edges: list[tuple[str, str, int]],
    distances: dict[str, str],
    current: str | None = None,
    visited: set[str] | None = None,
    active_edge: tuple[str, str] | None = None,
    step_text: str = "",
    algo_name: str = "",
    duration: float = STEP_DUR,
) -> CompositeVideoClip:
    if visited is None:
        visited = set()

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


def _dijkstra_steps() -> list[CompositeVideoClip]:
    n = NODE_POS
    e = EDGES_DIJKSTRA
    return [
        _make_step(
            n,
            e,
            {"S": "0", "A": INF, "B": INF, "C": INF},
            current="S",
            step_text="Inicjalizacja: d[S]=0, reszta=∞. Wybierz S (min d).",
            algo_name="Algorytm Dijkstry",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": INF},
            current="S",
            active_edge=("S", "A"),
            step_text="Relaksacja S→A: d[A]=0+2=2.  S→B: d[B]=0+5=5.",
            algo_name="Algorytm Dijkstry",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": "5"},
            current="A",
            visited={"S"},
            active_edge=("A", "C"),
            step_text="Zamknij S. Min=A(2). Relaksacja A→C: d[C]=2+3=5.",
            algo_name="Algorytm Dijkstry",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": "5"},
            current="B",
            visited={"S", "A"},
            active_edge=("B", "A"),
            step_text="Zamknij A. Min=B(5). B→A: 5+1=6>2, nie zmieniaj. B→C: 5+6=11>5.",
            algo_name="Algorytm Dijkstry",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": "5"},
            current="C",
            visited={"S", "A", "B"},
            step_text="Zamknij B. Min=C(5). Koniec!  Wynik: d={S:0, A:2, B:5, C:5}.",
            algo_name="Dijkstra -- WYNIK",
        ),
    ]


def _bellman_ford_steps() -> list[CompositeVideoClip]:
    n = NODE_POS
    e = EDGES_BF
    return [
        _make_step(
            n,
            e,
            {"S": "0", "A": INF, "B": INF, "C": INF},
            step_text="Bellman-Ford: relaksuj WSZYSTKIE krawędzie V-1=3 razy. Ujemne wagi OK!",
            algo_name="Algorytm Bellmana-Forda",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": "5"},
            active_edge=("S", "A"),
            step_text="Iteracja 1: S→A:2, A→C:5, S→B:5. Potem B→A: 5+(-4)=1 < 2 → A=1!",
            algo_name="Bellman-Ford -- iteracja 1",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "1", "B": "5", "C": "5"},
            active_edge=("B", "A"),
            step_text="B→A z ujemną wagą -4: d[A] poprawione z 2 na 1! (Dijkstra by to pominął!)",
            algo_name="Bellman-Ford -- ujemna waga",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "1", "B": "5", "C": "4"},
            active_edge=("A", "C"),
            step_text="Iteracja 2: A→C: 1+3=4 < 5 → C=4. Propagacja poprawionego A.",
            algo_name="Bellman-Ford -- iteracja 2",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "1", "B": "5", "C": "4"},
            step_text="Iteracja 3: brak zmian. V-ta iteracja: brak popraw → brak cyklu ujemnego.",
            algo_name="Bellman-Ford -- WYNIK, O(V*E)",
        ),
    ]


def _astar_steps() -> list[CompositeVideoClip]:
    n = NODE_POS
    e = EDGES_DIJKSTRA
    return [
        _make_step(
            n,
            e,
            {"S": "0", "A": INF, "B": INF, "C": INF},
            current="S",
            step_text="A*: f(n)=g(n)+h(n). Cel=C. h(S)=5, h(A)=3, h(B)=4, h(C)=0. f(S)=0+5=5.",
            algo_name="Algorytm A*",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": INF},
            current="S",
            active_edge=("S", "A"),
            step_text="Relaksuj S: A(g=2,f=2+3=5), B(g=5,f=5+4=9). Min f → A(5).",
            algo_name="A* -- rozwijanie S",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": "5"},
            current="A",
            visited={"S"},
            active_edge=("A", "C"),
            step_text="Rozwiń A(f=5): A→C: g=2+3=5, f=5+0=5. Min f → C(5) = CEL!",
            algo_name="A* -- rozwijanie A",
        ),
        _make_step(
            n,
            e,
            {"S": "0", "A": "2", "B": "5", "C": "5"},
            current="C",
            visited={"S", "A"},
            step_text="Dotarliśmy do C! Koszt=5. A* NIE przetwarza B (3 vs 4 w Dijkstrze).",
            algo_name="A* -- cel osiągnięty!",
        ),
    ]


def _comparison_slide() -> CompositeVideoClip:
    bg = ColorClip(size=(W, H), color=BG).with_duration(12.0)
    title = (
        _tc(
            text="Porównanie algorytmów",
            font_size=40,
            color="white",
            font=FONT_B,
        )
        .with_duration(12.0)
        .with_position(("center", 40))
    )
    rows = [
        ("Cecha", "Dijkstra", "Bellman-Ford", "A*"),
        ("Typ", "Zachłanny", "Prog. dynamiczne", "Heurystyczny"),
        ("Problem", "SSSP", "SSSP", "Single-pair"),
        ("Ujemne wagi", "NIE", "TAK", "NIE"),
        ("Cykl ujemny", "NIE wykrywa", "TAK wykrywa", "NIE"),
        ("Złożoność", "O((V+E)log V)", "O(V*E)", "Zależy od h(n)"),
    ]
    clips: list[VideoClip] = [bg, title]
    for i, row in enumerate(rows):
        y_pos = 120 + i * 85
        for j, cell in enumerate(row):
            x_pos = 60 + j * 300
            fs = 18 if i > 0 else 22
            color = "#64B5F6" if i == 0 else "#CFD8DC"
            tc = (
                _tc(
                    text=cell,
                    font_size=fs,
                    color=color,
                    font=FONT_B if i == 0 else FONT_R,
                )
                .with_duration(12.0)
                .with_position((x_pos, y_pos))
            )
            clips.append(tc)
    return CompositeVideoClip(clips, size=(W, H)).with_effects(
        [FadeIn(0.5), FadeOut(0.5)]
    )


def main() -> None:
    """Generate the Q02 shortest path visualization video."""
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
    print(f"Video saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
