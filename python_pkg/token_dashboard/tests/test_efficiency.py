from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess

import pytest

from python_pkg.token_dashboard import efficiency, gitcmd, survival

DAY = 86400.0
MONDAY = datetime(2026, 10, 5, 12, tzinfo=UTC).timestamp()


def _s(ts: float, usd: float, tag: str | None) -> efficiency.SessionCost:
    return efficiency.SessionCost(key=f"k{ts}{tag}", first_ts=ts, usd=usd, tag=tag)


def test_cost_per_done_counts_failed_sessions_against_done_ones() -> None:
    rows = [
        _s(MONDAY, 10.0, "DONE"),
        _s(MONDAY + 1, 6.0, "QUESTION"),
        _s(MONDAY + 2, 4.0, "DONE"),
        _s(MONDAY + 3, 99.0, None),  # pre-convention: excluded from the ratio
    ]
    (week,) = efficiency.done_weekly(rows)
    assert week["done"] == 2
    assert week["other"] == 1
    assert week["untagged"] == 1
    assert week["usd_per_done"] == pytest.approx(10.0)
    assert week["done_share"] == pytest.approx(2 / 3)


def test_week_with_no_done_has_no_ratio() -> None:
    (week,) = efficiency.done_weekly([_s(MONDAY, 5.0, "RUNNING")])
    assert week["usd_per_done"] is None


def test_cost_per_surviving_commit_and_pending() -> None:
    week_usd = {efficiency.week_of(MONDAY): 30.0}
    verdicts = [
        (MONDAY, "survived"),
        (MONDAY, "survived"),
        (MONDAY, "churned"),
        (MONDAY, "pending"),
    ]
    (week,) = efficiency.commits_weekly(verdicts, week_usd)
    assert (week["survived"], week["lost"], week["pending"]) == (2, 1, 1)
    assert week["usd_per_survivor"] == pytest.approx(15.0)


def test_cost_per_estimated_unit() -> None:
    rows = [_s(MONDAY, 8.0, None), _s(MONDAY + 5, 2.0, "DONE")]
    estimates = {rows[0].key: 30, rows[1].key: 10}
    (week,) = efficiency.estimate_weekly(rows, estimates)
    assert week["est_calls"] == 40
    assert week["usd_per_unit"] == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("added", "kept", "reverted", "expected"),
    [
        (10, 10, False, "survived"),
        (10, 5, False, "survived"),
        (10, 4, False, "churned"),
        (10, 10, True, "reverted"),
        (0, 0, False, "survived"),
    ],
)
def test_survival_rule(added: int, kept: int, *, reverted: bool, expected: str) -> None:
    assert survival.judge(added, kept, reverted=reverted) == expected


def _git(repo: Path, *args: str, when: float) -> str:
    stamp = f"@{int(when)} +0000"
    env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
    env |= {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "HOME": str(repo)}
    env |= {"GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    done = subprocess.run(
        [gitcmd.GIT, "-C", str(repo), *args],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _commit(repo: Path, name: str, text: str, when: float) -> str:
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name, when=when)
    _git(repo, "commit", "-qm", name, when=when)
    return _git(repo, "rev-parse", "HEAD", when=when)


def test_git_survival_against_a_real_repo(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", when=MONDAY)
    t0 = MONDAY - 40 * DAY
    kept = _commit(repo, "a.txt", "1\n2\n3\n4\n", t0)
    churn = _commit(repo, "b.txt", "1\n2\n3\n4\n", t0 + 1)
    _commit(repo, "b.txt", "x\ny\nz\n4\n", t0 + 2 * DAY)
    young = _commit(repo, "c.txt", "1\n", MONDAY)
    now = MONDAY + 1
    assert survival.evaluate(str(repo), kept[:8], now).verdict == "survived"
    churned = survival.evaluate(str(repo), churn, now)
    assert (churned.verdict, churned.added, churned.kept) == ("churned", 4, 1)
    assert survival.evaluate(str(repo), young, now).verdict == "pending"
    assert survival.evaluate(str(repo), "deadbeef", now).verdict == "unknown"
    assert survival.evaluate(str(tmp_path / "nope"), kept, now).verdict == "unknown"


def test_git_revert_within_window_is_reverted(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", when=MONDAY)
    t0 = MONDAY - 40 * DAY
    _commit(repo, "a.txt", "base\n", t0 - 10)
    bad = _commit(repo, "b.txt", "1\n", t0)
    _git(repo, "revert", "--no-edit", bad, when=t0 + DAY)
    assert survival.evaluate(str(repo), bad, MONDAY).verdict == "reverted"


def test_update_judges_old_commits_and_stops_at_the_deadline(tmp_path: Path) -> None:
    from python_pkg.token_dashboard import schema

    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", when=MONDAY)
    old = _commit(repo, "a.txt", "1\n", MONDAY - 40 * DAY)
    conn = schema.connect(tmp_path / "t.sqlite")
    rows = [
        (old, str(repo), MONDAY - 40 * DAY, "s", 0),
        ("f" * 40, "x", MONDAY, "s", 0),
    ]
    conn.executemany("INSERT INTO session_commits VALUES (?,?,?,?,?)", rows)
    assert not survival.update(conn, MONDAY, deadline=0.0, clock=lambda: 1.0)
    assert survival.update(conn, MONDAY, deadline=2.0, clock=lambda: 1.0)
    efficiency.rebuild(conn, MONDAY)
    verdicts = conn.execute("SELECT verdict FROM commit_verdicts").fetchall()
    payload = conn.execute("SELECT value FROM meta WHERE key='efficiency'").fetchone()
    conn.close()
    assert verdicts == [("survived",)]
    assert '"pending": 1' in payload[0]
