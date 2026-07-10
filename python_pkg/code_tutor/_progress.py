"""Persist and load study plans and progress state.

Storage layout::

    ~/.config/code_tutor/
    └── <sha256 of absolute codebase path>/
        ├── plan.json          # created by ``analyze``
        ├── progress.json      # updated after each lesson
        └── sessions/
            └── YYYY-MM-DD.jsonl  # full lesson records for analysis
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import datetime
import hashlib
import json
from pathlib import Path
from typing import TypedDict, cast

from python_pkg.code_tutor._analyzer import CodeItem

# ---------------------------------------------------------------------------
# TypedDicts matching the plan.json / progress.json schemas
# ---------------------------------------------------------------------------


class ItemData(TypedDict):
    """Schema for a single code item entry in ``plan.json``."""

    id: str
    file: str
    type: str
    name: str
    start_line: int
    end_line: int
    class_name: str
    depends_on: list[str]


class SessionData(TypedDict):
    """Schema for a session block in ``plan.json``."""

    id: int
    title: str
    items: list[ItemData]


class PlanData(TypedDict):
    """Top-level schema of ``plan.json``."""

    codebase_path: str
    created_at: str
    total_items: int
    source_fingerprint: str
    sessions: list[SessionData]


class ProgressData(TypedDict):
    """Schema of ``progress.json`` tracking what the user has studied."""

    learned: list[str]
    struggled: list[str]
    skipped: list[str]
    last_session: str


# ---------------------------------------------------------------------------
# Full lesson record — written to sessions/YYYY-MM-DD.jsonl for analysis
# ---------------------------------------------------------------------------


@dataclass
class LessonRecord:
    """Complete transcript of one Socratic lesson.

    Stored as a JSON line so the file can be streamed / analysed later.

    Attributes:
        timestamp: ISO-8601 UTC timestamp of the lesson.
        item_id: Dotted ID of the code item studied.
        file: Relative path of the source file.
        lines: ``"start-end"`` line range string.
        snippet: The exact source text shown to the user.
        outcome: ``"learned"``, ``"struggled"``, or ``"skipped"``.
        answers: Mapping of question label to the user's answer.
        improvement: User's free-text code improvement idea (may be empty).
        verdict: Final LLM verdict: ``"PASS"``, ``"FAIL"``, or ``"skipped"``.
        attempt: Which attempt produced the final verdict (1-3).
    """

    timestamp: str
    item_id: str
    file: str
    lines: str
    snippet: str
    outcome: str
    answers: dict[str, str]
    improvement: str
    verdict: str
    attempt: int
    challenge_result: str = ""


def append_session_record(codebase: Path, record: LessonRecord) -> None:
    """Append *record* as a JSON line to today's session log for *codebase*.

    Creates ``sessions/`` if it does not exist.  Each line is a self-contained
    JSON object so the file can be streamed with ``jq``.

    Args:
        codebase: Root directory of the codebase being studied.
        record: Lesson record to persist.
    """
    sessions_dir = config_dir(codebase) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now(tz=datetime.timezone.utc).date().isoformat()
    log_file = sessions_dir / f"{today}.jsonl"
    line = json.dumps(asdict(record), ensure_ascii=False)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------------------
# Config directory helpers
# ---------------------------------------------------------------------------


def config_dir(codebase: Path) -> Path:
    """Return the config directory for *codebase*.

    The directory name is the SHA-256 hex digest of the absolute path string,
    so different codebases never collide.

    Args:
        codebase: Root directory of the codebase being studied.

    Returns:
        ``~/.config/code_tutor/<hex>/`` (not guaranteed to exist).
    """
    path_hash = hashlib.sha256(str(codebase.resolve()).encode()).hexdigest()
    return Path.home() / ".config" / "code_tutor" / path_hash


def load_plan(codebase: Path) -> PlanData | None:
    """Load the saved plan for *codebase*, or return ``None`` if absent.

    Args:
        codebase: Root directory of the codebase.

    Returns:
        Parsed ``PlanData`` dict, or ``None`` when no plan file exists.
    """
    plan_file = config_dir(codebase) / "plan.json"
    if not plan_file.exists():
        return None
    return cast("PlanData", json.loads(plan_file.read_text(encoding="utf-8")))


def save_plan(codebase: Path, plan: dict[str, object]) -> None:
    """Persist *plan* to ``plan.json`` for *codebase*.

    Creates the config directory if it does not already exist.

    Args:
        codebase: Root directory of the codebase.
        plan: Plan dict (as returned by ``build_plan``).
    """
    dest = config_dir(codebase)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")


def load_progress(codebase: Path) -> ProgressData:
    """Load progress for *codebase*, returning an empty record if none exists.

    Args:
        codebase: Root directory of the codebase.

    Returns:
        ``ProgressData`` dict with learned/struggled/skipped lists.
    """
    progress_file = config_dir(codebase) / "progress.json"
    if not progress_file.exists():
        return {
            "learned": [],
            "struggled": [],
            "skipped": [],
            "last_session": "",
        }
    return cast("ProgressData", json.loads(progress_file.read_text(encoding="utf-8")))


def save_progress(codebase: Path, progress: ProgressData) -> None:
    """Write *progress* to ``progress.json`` for *codebase*.

    Args:
        codebase: Root directory of the codebase.
        progress: Progress dict to persist.
    """
    dest = config_dir(codebase)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "progress.json").write_text(
        json.dumps(progress, indent=2), encoding="utf-8"
    )


def item_from_data(data: ItemData) -> CodeItem:
    """Convert an ``ItemData`` TypedDict to a ``CodeItem`` dataclass.

    Args:
        data: Dict loaded from ``plan.json``.

    Returns:
        Corresponding ``CodeItem`` with all fields populated.
    """
    return CodeItem(
        id=data["id"],
        file=data["file"],
        type=data["type"],
        name=data["name"],
        start_line=data["start_line"],
        end_line=data["end_line"],
        class_name=data["class_name"],
        depends_on=data["depends_on"],
    )
