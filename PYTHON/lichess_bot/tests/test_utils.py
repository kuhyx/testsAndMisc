"""Tests for utility functions."""

from PYTHON.lichess_bot.utils import backoff_sleep


def test_backoff_sleep_increments_and_caps(monkeypatch):
    """Test that backoff sleep increments and respects the cap."""
    slept = []

    def fake_sleep(sec):
        slept.append(sec)

    monkeypatch.setattr("time.sleep", fake_sleep)

    b = 0
    b = backoff_sleep(b, base=0.1, cap=0.3)
    b = backoff_sleep(b, base=0.1, cap=0.3)
    b = backoff_sleep(b, base=0.1, cap=0.3)
    assert b >= 1
    assert len(slept) == 3
    # Expected sleep values: first=0.1, second=0.2, third=0.3 (capped)
    assert slept[0] == 0.1
    assert slept[1] == 0.2
    assert slept[2] == 0.3
