"""Tests for _q02_algorithm_steps module."""

from __future__ import annotations


def test_dijkstra_steps() -> None:
    """_dijkstra_steps returns a list of steps."""
    from python_pkg.praca_magisterska_video._q02_algorithm_steps import (
        _dijkstra_steps,
    )

    steps = _dijkstra_steps()
    assert isinstance(steps, list)
    assert len(steps) == 5


def test_bellman_ford_steps() -> None:
    """_bellman_ford_steps returns a list of steps."""
    from python_pkg.praca_magisterska_video._q02_algorithm_steps import (
        _bellman_ford_steps,
    )

    steps = _bellman_ford_steps()
    assert isinstance(steps, list)
    assert len(steps) == 5


def test_astar_steps() -> None:
    """_astar_steps returns a list of steps."""
    from python_pkg.praca_magisterska_video._q02_algorithm_steps import (
        _astar_steps,
    )

    steps = _astar_steps()
    assert isinstance(steps, list)
    assert len(steps) == 4


def test_comparison_slide() -> None:
    """_comparison_slide returns a CompositeVideoClip."""
    from python_pkg.praca_magisterska_video._q02_algorithm_steps import (
        _comparison_slide,
    )

    result = _comparison_slide()
    assert result is not None
