"""Tests for _q24_classical module."""

from __future__ import annotations


def test_detection_concept() -> None:
    """_detection_concept returns slides."""
    from python_pkg.praca_magisterska_video._q24_classical import (
        _detection_concept,
    )

    slides = _detection_concept()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_hog_svm_demo() -> None:
    """_hog_svm_demo returns slides."""
    from python_pkg.praca_magisterska_video._q24_classical import (
        _hog_svm_demo,
    )

    slides = _hog_svm_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_viola_jones_demo() -> None:
    """_viola_jones_demo returns slides."""
    from python_pkg.praca_magisterska_video._q24_classical import (
        _viola_jones_demo,
    )

    slides = _viola_jones_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1
