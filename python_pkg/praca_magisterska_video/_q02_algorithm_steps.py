"""Algorithm step definitions for Q02 shortest path visualization.

Contains step sequences for Dijkstra, Bellman-Ford, A*, and the
comparison slide used in the final video.
"""

from __future__ import annotations

from moviepy import (
    ColorClip,
    CompositeVideoClip,
    VideoClip,
)
from moviepy.video.fx import FadeIn, FadeOut

from python_pkg.praca_magisterska_video.visualize_q02 import (
    BG,
    EDGES_BF,
    EDGES_DIJKSTRA,
    FONT_B,
    FONT_R,
    INF,
    NODE_POS,
    H,
    W,
    _make_step,
    _StepConfig,
    _tc,
)


def _dijkstra_steps() -> list[CompositeVideoClip]:
    n = NODE_POS
    e = EDGES_DIJKSTRA
    return [
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": INF, "B": INF, "C": INF},
                current="S",
                step_text="Inicjalizacja: d[S]=0, reszta=∞. Wybierz S (min d).",
                algo_name="Algorytm Dijkstry",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": INF},
                current="S",
                active_edge=("S", "A"),
                step_text="Relaksacja S→A: d[A]=0+2=2.  S→B: d[B]=0+5=5.",
                algo_name="Algorytm Dijkstry",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": "5"},
                current="A",
                visited={"S"},
                active_edge=("A", "C"),
                step_text="Zamknij S. Min=A(2). Relaksacja A→C: d[C]=2+3=5.",
                algo_name="Algorytm Dijkstry",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": "5"},
                current="B",
                visited={"S", "A"},
                active_edge=("B", "A"),
                step_text=(
                    "Zamknij A. Min=B(5). B→A: 5+1=6>2, nie zmieniaj. B→C: 5+6=11>5."
                ),
                algo_name="Algorytm Dijkstry",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": "5"},
                current="C",
                visited={"S", "A", "B"},
                step_text=(
                    "Zamknij B. Min=C(5). Koniec! Wynik: d={S:0, A:2, B:5, C:5}."
                ),
                algo_name="Dijkstra -- WYNIK",
            ),
        ),
    ]


def _bellman_ford_steps() -> list[CompositeVideoClip]:
    n = NODE_POS
    e = EDGES_BF
    return [
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": INF, "B": INF, "C": INF},
                step_text=(
                    "Bellman-Ford: relaksuj WSZYSTKIE "
                    "krawędzie V-1=3 razy. Ujemne wagi OK!"
                ),
                algo_name="Algorytm Bellmana-Forda",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": "5"},
                active_edge=("S", "A"),
                step_text=(
                    "Iteracja 1: S→A:2, A→C:5, S→B:5. Potem B→A: 5+(-4)=1 < 2 → A=1!"
                ),
                algo_name="Bellman-Ford -- iteracja 1",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "1", "B": "5", "C": "5"},
                active_edge=("B", "A"),
                step_text=(
                    "B→A z ujemną wagą -4: d[A] poprawione "
                    "z 2 na 1! (Dijkstra by to pominął!)"
                ),
                algo_name="Bellman-Ford -- ujemna waga",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "1", "B": "5", "C": "4"},
                active_edge=("A", "C"),
                step_text=(
                    "Iteracja 2: A→C: 1+3=4 < 5 → C=4. Propagacja poprawionego A."
                ),
                algo_name="Bellman-Ford -- iteracja 2",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "1", "B": "5", "C": "4"},
                step_text=(
                    "Iteracja 3: brak zmian. V-ta iteracja: "
                    "brak popraw → brak cyklu ujemnego."
                ),
                algo_name="Bellman-Ford -- WYNIK, O(V*E)",
            ),
        ),
    ]


def _astar_steps() -> list[CompositeVideoClip]:
    n = NODE_POS
    e = EDGES_DIJKSTRA
    return [
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": INF, "B": INF, "C": INF},
                current="S",
                step_text=(
                    "A*: f(n)=g(n)+h(n). Cel=C. "
                    "h(S)=5, h(A)=3, h(B)=4, h(C)=0. f(S)=0+5=5."
                ),
                algo_name="Algorytm A*",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": INF},
                current="S",
                active_edge=("S", "A"),
                step_text=("Relaksuj S: A(g=2,f=2+3=5), B(g=5,f=5+4=9). Min f → A(5)."),
                algo_name="A* -- rozwijanie S",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": "5"},
                current="A",
                visited={"S"},
                active_edge=("A", "C"),
                step_text=("Rozwiń A(f=5): A→C: g=2+3=5, f=5+0=5. Min f → C(5) = CEL!"),
                algo_name="A* -- rozwijanie A",
            ),
        ),
        _make_step(
            _StepConfig(
                n,
                e,
                {"S": "0", "A": "2", "B": "5", "C": "5"},
                current="C",
                visited={"S", "A"},
                step_text=(
                    "Dotarliśmy do C! Koszt=5. "
                    "A* NIE przetwarza B (3 vs 4 w Dijkstrze)."
                ),
                algo_name="A* -- cel osiągnięty!",
            ),
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
