import builtins

from PYTHON.lichess_bot.utils import backoff_sleep


def test_backoff_sleep_increments_and_caps(monkeypatch):
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
    # 0.1, 0.2, 0.3 (capped)
    assert slept[0] == 0.1 and slept[1] == 0.2 and slept[2] == 0.3
