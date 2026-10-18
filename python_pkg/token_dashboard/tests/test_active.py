from __future__ import annotations

from python_pkg.token_dashboard import active


def test_gap_over_limit_contributes_zero_not_the_limit() -> None:
    spans = active.intervals([0, 60, 120, 1000, 1030])
    assert spans == [(0, 120), (1000, 1030)]
    assert active.measure(spans) == 150


def test_union_bridges_short_gaps_between_files() -> None:
    main = [(0.0, 100.0)]
    sub = [(250.0, 400.0)]  # 150 s after main went quiet: still active
    far = [(2000.0, 2010.0)]
    assert active.measure(main + sub + far) == 410


def test_overlapping_intervals_count_once() -> None:
    assert active.measure([(0.0, 100.0), (50.0, 150.0)]) == 150


def test_clip_to_a_prompt_window() -> None:
    spans = [(0.0, 100.0), (1000.0, 1100.0)]
    assert active.measure(spans, 50.0, 1050.0) == 100
    assert active.measure([], 0.0, 10.0) == 0


def test_empty_and_single_stamp() -> None:
    assert active.intervals([]) == []
    assert active.intervals([5.0]) == [(5.0, 5.0)]
