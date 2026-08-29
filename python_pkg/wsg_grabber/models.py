"""Plain-data records shared across the package.

Everything crossing a module boundary is a frozen dataclass or an enum, so the
pure planning code can be driven from hand-built literals and the GUI never has
to be constructed to test a decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Verdict(StrEnum):
    """What the user decided about a video.

    The member is ``SKIP`` rather than ``PASS`` only because ruff's S105 reads a
    name of ``PASS`` as a hardcoded password and this repo forbids ``noqa``. The
    stored value stays ``"pass"``, which is the word the UI shows.
    """

    KEEP = "keep"
    SKIP = "pass"


class TaskKind(StrEnum):
    """What the background worker should do next."""

    DOWNLOAD = "download"
    SCAN = "scan"
    IDLE = "idle"


class Emptiness(StrEnum):
    """Why the reviewer has nothing to show."""

    NOT_EMPTY = "not_empty"
    WAITING = "waiting"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True, slots=True)
class Size:
    """A pixel size."""

    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ThreadRef:
    """A thread as advertised by ``threads.json``."""

    thread_no: int
    api_last_modified: int


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """An attachment described by a post, before anything is downloaded.

    ``md5`` is the API's own ``base64(md5(file_bytes))`` and is the identity of
    the file everywhere in this package.
    """

    md5: str
    tim: int
    ext: str
    orig_name: str
    fsize: int
    width: int
    height: int
    thread_no: int
    post_no: int


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """A downloaded video waiting for a verdict."""

    md5: str
    path: Path
    orig_name: str
    fsize: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class FileMove:
    """A planned relocation. Applying it is the only filesystem write."""

    md5: str
    src: Path
    dst: Path


@dataclass(frozen=True, slots=True)
class ReviewedItem:
    """A verdict recorded in the index, and therefore reversible.

    ``reviewed_name`` is the name the file was given in keep/ or trash/, which
    differs from ``item.path.name`` whenever a collision forced a rename. Undo
    needs it to find the file again, which is why it is persisted rather than
    held in memory.
    """

    item: ReviewItem
    choice: Verdict
    reviewed_name: str


@dataclass(frozen=True, slots=True)
class ResumePlan:
    """How to continue a partial download."""

    offset: int
    discard: bool


class Outcome(StrEnum):
    """How a download ended."""

    COMPLETED = "completed"
    NOT_FOUND = "not_found"
    TRANSIENT = "transient"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class JsonResponse:
    """The result of a conditional GET against the API."""

    payload: object | None
    last_modified: str | None
    not_modified: bool
    not_found: bool


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """The result of streaming one file to disk."""

    outcome: Outcome
    bytes_done: int
    retry_after: float | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewCommand:
    """Everything the GUI must render or do, already decided.

    The window applies this verbatim; it never formats a string or picks a file.
    """

    play: Path | None
    stop: bool
    status: str
    title: str
    filename: str
    verdicts_enabled: bool
    undo_enabled: bool
    quit_app: bool


@dataclass(frozen=True, slots=True)
class FileReady:
    """A newly downloaded video is available for review."""

    item: ReviewItem


@dataclass(frozen=True, slots=True)
class Indexed:
    """The catalogue scan learned about more files."""

    known: int


@dataclass(frozen=True, slots=True)
class Downloaded:
    """Running count of files fetched this session."""

    count: int


@dataclass(frozen=True, slots=True)
class ScanFinished:
    """The board has been walked and every known file downloaded."""


@dataclass(frozen=True, slots=True)
class WorkerFailed:
    """The background worker died; the message is shown in the status bar."""

    message: str


DownloadEvent = FileReady | Indexed | Downloaded | ScanFinished | WorkerFailed
