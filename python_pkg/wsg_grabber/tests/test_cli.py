"""Tests for the command-line interface."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import app, cli, db, logs, paths, store
from python_pkg.wsg_grabber.models import RemoteFile

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def fake_session() -> Iterator[app.Session]:
    """Build a session over a sandboxed index with no worker.

    Yields:
        app.Session: Session closed afterwards.
    """
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    built = app.Session(conn=conn, events=queue.SimpleQueue(), stop=threading.Event())
    try:
        yield built
    finally:
        conn.close()


def test_parser_defaults_to_the_reviewer() -> None:
    assert cli.build_parser().parse_args([]).command is None
    assert cli.build_parser().parse_args(["review"]).command == "review"


def test_parser_exposes_the_subcommands() -> None:
    assert cli.build_parser().parse_args(["stats"]).command == "stats"
    parsed = cli.build_parser().parse_args(["scrape", "--seconds", "5"])
    assert parsed.command == "scrape"
    assert parsed.seconds == pytest.approx(5.0)


def test_help_mentions_that_nothing_is_deleted() -> None:
    text = cli.build_parser().format_help()
    assert "Nothing is ever deleted" in text
    assert "trash" in text


def test_stats_reports_every_state(capsys: pytest.CaptureFixture[str]) -> None:
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    store.record_files(
        conn,
        [
            RemoteFile(
                md5="A" * 24,
                tim=1,
                ext=".webm",
                orig_name="x",
                fsize=1,
                width=1,
                height=1,
                thread_no=1,
                post_no=1,
            ),
        ],
    )
    conn.close()

    assert cli.main(["stats"]) == 0
    out = capsys.readouterr().out
    assert "known files  1" in out
    assert "new          1" in out
    assert "never emptied automatically" in out


def test_scrape_runs_and_shuts_down(
    fake_session: app.Session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ticks = {"n": 0}

    def fake_sleep(_seconds: float) -> None:
        ticks["n"] += 1

    with (
        patch.object(app, "open_session", return_value=fake_session),
        patch.object(fake_session, "shutdown") as stopped,
        patch(
            "python_pkg.wsg_grabber.cli.time.monotonic",
            side_effect=[0.0, 1.0, 99.0, 99.0],
        ),
    ):
        assert cli.scrape(5.0, sleeper=fake_sleep) == 0

    assert ticks["n"] >= 1
    stopped.assert_called_once()
    assert "scraping /wsg/" in capsys.readouterr().out


def test_scrape_reports_progress_periodically(
    fake_session: app.Session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch.object(app, "open_session", return_value=fake_session),
        patch.object(fake_session, "shutdown"),
        patch(
            "python_pkg.wsg_grabber.cli.time.monotonic",
            side_effect=[0.0, 999.0, 999.0, 999.0],
        ),
    ):
        cli.scrape(1.0, sleeper=lambda _s: None)
    assert "known 0" in capsys.readouterr().out


def test_scrape_handles_an_interrupt(
    fake_session: app.Session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def interrupt(_seconds: float) -> None:
        raise KeyboardInterrupt

    with (
        patch.object(app, "open_session", return_value=fake_session),
        patch.object(fake_session, "shutdown") as stopped,
    ):
        assert cli.scrape(0.0, sleeper=interrupt) == 0
    stopped.assert_called_once()
    assert "stopping" in capsys.readouterr().out


def test_main_dispatches_to_the_reviewer() -> None:
    with patch.object(cli, "open_reviewer", return_value=0) as opened:
        assert cli.main([]) == 0
    opened.assert_called_once()


def test_main_dispatches_to_scrape() -> None:
    with patch.object(cli, "scrape", return_value=0) as scraped:
        assert cli.main(["scrape", "--seconds", "2"]) == 0
    assert scraped.call_args.args[0] == pytest.approx(2.0)


def test_open_reviewer_wires_the_window_to_the_player(
    fake_session: app.Session,
) -> None:
    window = MagicMock()
    window.video_wid.return_value = 4321
    with (
        patch.object(app, "open_session", return_value=fake_session),
        patch(
            "python_pkg.wsg_grabber.cli.ui.ReviewWindow",
            return_value=window,
        ) as built,
        patch("python_pkg.wsg_grabber.cli.player.MpvPlayer") as made_player,
    ):
        assert cli.open_reviewer() == 0

    made_player.assert_called_once_with(4321, paths.ipc_socket_path())
    window.attach_player.assert_called_once()
    window.run.assert_called_once()
    callbacks = built.call_args.args[2]
    assert callbacks.commit == fake_session.commit
    assert callbacks.shutdown == fake_session.shutdown


def test_log_level_flags_are_exposed() -> None:
    parsed = cli.build_parser().parse_args(["--log-level", "debug", "--echo-log"])
    assert parsed.log_level == "debug"
    assert parsed.echo_log
    assert cli.build_parser().parse_args([]).log_level == "info"


def test_running_a_command_writes_a_session_log() -> None:
    assert cli.main(["stats"]) == 0
    written = sorted(logs.logs_dir().glob("session-*.jsonl"))
    assert written
    assert "session.start" in written[-1].read_text(encoding="utf-8")


def test_logs_command_reports_where_logs_live(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli.main(["stats"])
    capsys.readouterr()
    assert cli.main(["logs"]) == 0
    out = capsys.readouterr().out
    assert str(logs.logs_dir()) in out
    assert "newest session" in out
    assert "jq" in out


def test_logs_command_before_anything_has_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logs.logs_dir().mkdir(parents=True, exist_ok=True)
    for stale in logs.logs_dir().glob("*.jsonl"):
        stale.unlink()
    assert cli.show_logs() == 0
    assert "no session logs yet" in capsys.readouterr().out


def test_summarise_counts_events_and_skips_junk(tmp_path: Path) -> None:
    sample = tmp_path / "s.jsonl"
    sample.write_text(
        '{"event":"a","level":"info"}\n'
        "not json at all\n"
        '{"event":"a","level":"error"}\n'
        '{"event":"b","level":"info"}\n',
        encoding="utf-8",
    )
    text = cli.summarise(sample)
    assert "error=1" in text
    assert "info=2" in text
    assert "a" in text


def test_a_failed_player_start_does_not_strand_the_worker(
    fake_session: app.Session,
) -> None:
    """The worker is non-daemon; without cleanup the process never exits."""
    window = MagicMock()
    window.video_wid.return_value = 1
    with (
        patch.object(app, "open_session", return_value=fake_session),
        patch("python_pkg.wsg_grabber.cli.ui.ReviewWindow", return_value=window),
        patch(
            "python_pkg.wsg_grabber.cli.player.MpvPlayer",
            side_effect=TimeoutError("mpv never came up"),
        ),
        patch.object(fake_session, "shutdown") as stopped,
        pytest.raises(TimeoutError),
    ):
        cli.open_reviewer()
    stopped.assert_called_once()
