"""Row types one transcript file contributes to the store (see :mod:`walk`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from python_pkg.token_dashboard.detail_rows import DetailRows

if TYPE_CHECKING:
    from python_pkg.token_dashboard import active


@dataclass(frozen=True)
class TurnRow:
    """One deduplicated API call, priced."""

    ts: float
    model: str
    usd: float
    context: int
    prompt_idx: int
    usage: dict[str, int]


@dataclass(frozen=True)
class PromptRow:
    """One typed user prompt."""

    idx: int
    ts: float
    prompt_id: str
    text: str


@dataclass
class ToolRow:
    """Calls of one tool inside one prompt."""

    prompt_idx: int
    name: str
    calls: int = 0
    result_tokens: int = 0
    usd: float = 0.0
    carry_usd: float = 0.0
    # Settled by the carry tracker too, but not stored per tool (the calls
    # table holds creation per call).
    create_usd: float = 0.0
    carry_calls: int = 0


@dataclass(frozen=True)
class AgentCall:
    """An ``Agent`` tool call: the spawn point of a subagent."""

    tool_use_id: str
    agent_id: str
    prompt_idx: int
    ts: float
    description: str
    subagent_type: str
    model: str
    result_ts: float
    status: str


@dataclass(frozen=True)
class Commit:
    """A commit hash printed by a Bash ``git commit`` in this file."""

    prompt_idx: int
    ts: float
    end_ts: float
    sha: str
    repo: str


@dataclass
class FileRows:
    """The row lists one transcript file contributes."""

    turns: list[TurnRow] = field(default_factory=list)
    prompts: list[PromptRow] = field(default_factory=list)
    tools: list[ToolRow] = field(default_factory=list)
    agent_calls: list[AgentCall] = field(default_factory=list)
    intervals: list[active.Span] = field(default_factory=list)
    lever_tables: list[tuple[float, str]] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    messages: list[tuple[float, str]] = field(default_factory=list)
    detail: DetailRows = field(default_factory=DetailRows)


@dataclass
class FileFacts:
    """Everything one transcript file contributes to the store."""

    key: str
    session_id: str
    parent_session: str | None
    cwd: str | None
    meta: dict[str, Any]
    rows: FileRows = field(default_factory=FileRows)
    final_tag: str | None = None
    span: tuple[float, float] = (0.0, 0.0)
