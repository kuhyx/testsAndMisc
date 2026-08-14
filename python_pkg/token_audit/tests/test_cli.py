from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_audit import __main__ as cli

if TYPE_CHECKING:
    from pathlib import Path


def _transcript(
    root: Path,
    name: str = "s1",
    turns: int = 2,
    *,
    image: bool = False,
) -> Path:
    project = root / "proj"
    project.mkdir(exist_ok=True)
    records = []
    if image:
        records += [
            {
                "cwd": "/home/kuhy/demo",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "i1",
                            "name": "Read",
                            "input": {"file_path": "/shot.png"},
                        },
                    ],
                },
            },
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "i1",
                            "content": "x" * 400,
                        },
                    ],
                },
            },
        ]
    for index in range(turns):
        records.append(
            {
                "cwd": "/home/kuhy/demo",
                "message": {
                    "model": "claude-opus-5",
                    "usage": {
                        "output_tokens": 10,
                        "cache_read_input_tokens": 100 * index,
                        "cache_creation_input_tokens": 50,
                    },
                },
            },
        )
    path = project / f"{name}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


def test_no_data_exits_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.main(["--root", str(tmp_path), "--no-write"])
    assert code == cli.EXIT_NO_DATA
    assert "No transcripts" in capsys.readouterr().err


def test_transcript_without_usage_is_skipped(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "empty.jsonl").write_text(
        '{"message": {"content": []}}', encoding="utf-8"
    )
    assert cli.main(["--root", str(tmp_path), "--no-write"]) == cli.EXIT_NO_DATA


def test_successful_run_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _transcript(tmp_path, image=True)
    out_dir = tmp_path / "out"
    code = cli.main(["--root", str(tmp_path), "--out", str(out_dir), "--days", "36500"])
    assert code == 0
    captured = capsys.readouterr()
    assert "# Claude Code token audit" in captured.out
    assert (out_dir / "WEEKLY.md").exists()
    assert (out_dir / "weekly.json").exists()
    assert "Analysed 1 sessions" in captured.err


def test_no_write_leaves_no_files(tmp_path: Path) -> None:
    _transcript(tmp_path)
    out_dir = tmp_path / "out"
    cli.main(
        [
            "--root",
            str(tmp_path),
            "--out",
            str(out_dir),
            "--days",
            "36500",
            "--no-write",
        ]
    )
    assert not out_dir.exists()


def test_json_flag_emits_parsable_snapshot(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _transcript(tmp_path)
    cli.main(
        ["--root", str(tmp_path), "--days", "36500", "--no-write", "--json"],
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["sessions"] == 1
    assert payload["weighted_total"] > 0


def test_explicit_since_and_until_window(tmp_path: Path) -> None:
    _transcript(tmp_path)
    code = cli.main(
        [
            "--root",
            str(tmp_path),
            "--since",
            "0",
            "--until",
            "99999999999",
            "--no-write",
        ],
    )
    assert code == 0


def test_until_before_files_yields_no_data(tmp_path: Path) -> None:
    _transcript(tmp_path)
    code = cli.main(
        ["--root", str(tmp_path), "--since", "0", "--until", "1", "--no-write"]
    )
    assert code == cli.EXIT_NO_DATA


def test_drift_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _transcript(tmp_path)
    monkeypatch.setattr(cli.attribute, "reconcile", lambda *_: 0.5)
    code = cli.main(["--root", str(tmp_path), "--days", "36500", "--no-write"])
    assert code == cli.EXIT_DRIFT
    assert "RECONCILIATION FAILED" in capsys.readouterr().err


def test_second_run_reports_delta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _transcript(tmp_path)
    out_dir = tmp_path / "out"
    args = ["--root", str(tmp_path), "--out", str(out_dir), "--days", "36500"]
    cli.main(args)
    capsys.readouterr()
    cli.main(args)
    assert "Week over week" in capsys.readouterr().out


def test_parser_defaults() -> None:
    args = cli._build_parser().parse_args([])
    assert args.days == cli.DEFAULT_DAYS
    assert args.since is None
    assert args.json is False


def test_module_entrypoint_is_wired() -> None:
    assert callable(cli.main)


@pytest.mark.parametrize("flag", ["--help"])
def test_help_exits_zero(flag: str) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([flag])
    assert excinfo.value.code == 0
