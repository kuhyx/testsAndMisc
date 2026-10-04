from __future__ import annotations

import pytest

from python_pkg.token_audit import history


def _entry(**over: object) -> dict[str, object]:
    return {"lever": "L", "metric": "m", "baseline": 100.0, **over}


@pytest.mark.parametrize(
    ("baseline", "actual", "lower", "outcome"),
    [
        (0.0, 5.0, True, "no baseline"),
        (100.0, 102.0, True, "no effect"),
        (100.0, 50.0, True, "helped"),
        (100.0, 150.0, True, "regressed"),
        (100.0, 150.0, False, "helped"),
        (100.0, 50.0, False, "regressed"),
    ],
)
def test_outcome_classes(
    baseline: float, actual: float, outcome: str, *, lower: bool
) -> None:
    assert history._outcome(baseline, actual, lower_is_better=lower) == outcome


def test_prediction_note_variants() -> None:
    assert history._prediction_note(100, None, 50) == ""
    assert history._prediction_note(100, 100, 50) == ""
    assert history._prediction_note(100, 50, 50) == "prediction held"
    assert history._prediction_note(100, 50, 100) == "prediction off by 100%"


def test_score_measured_entry() -> None:
    verdicts = history.score(
        [_entry(predicted=50.0)],
        {"metrics": {"m": 50}},
    )
    (verdict,) = verdicts
    assert verdict.outcome == "helped"
    assert verdict.actual == 50.0
    assert verdict.predicted == 50.0
    assert verdict.note == "prediction held"


def test_score_higher_is_better_without_prediction() -> None:
    (verdict,) = history.score(
        [_entry(lower_is_better=False)],
        {"metrics": {"m": 200}},
    )
    assert verdict.outcome == "helped"
    assert verdict.predicted is None
    assert verdict.note == ""


def test_score_unmeasured_metric() -> None:
    (verdict,) = history.score([_entry(predicted=1)], {"metrics": {}})
    assert verdict.outcome == "unmeasured"
    assert verdict.actual is None
    assert verdict.predicted == 1.0


def test_score_unmeasured_without_lever_or_metrics_key() -> None:
    entry = {"metric": "m", "baseline": 1}
    (verdict,) = history.score([entry], {})
    assert verdict.lever == "?"
    assert verdict.outcome == "unmeasured"
