from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import walk
from python_pkg.token_dashboard.tests.conftest import (
    assistant,
    prompt,
    result,
    usd_opus_output,
    use,
    write,
)

if TYPE_CHECKING:
    from pathlib import Path


def _main(tmp_path: Path, records: list[dict[str, object]]) -> walk.FileFacts:
    path = write(tmp_path / "proj" / "sess-1.jsonl", records)
    return walk.walk_file(path, tmp_path)


def test_one_api_message_written_as_three_records_is_priced_once(
    tmp_path: Path,
) -> None:
    blocks = [use("t1", "Bash", command="ls"), use("t2", "Read", file_path="/a")]
    facts = _main(
        tmp_path,
        [
            prompt("do it", 0),
            assistant("m1", 1, blocks=[{"type": "thinking", "thinking": ""}]),
            assistant("m1", 1, blocks=blocks[:1]),
            assistant("m1", 1, blocks=blocks[1:]),
            result("t1", 2),
            result("t2", 2),
        ],
    )
    assert len(facts.rows.turns) == 1
    assert facts.rows.turns[0].usd == pytest.approx(usd_opus_output(1000))
    # The one turn's dollars split evenly across the two tools it issued.
    by_name = {t.name: t for t in facts.rows.tools}
    assert by_name["Bash"].usd == pytest.approx(usd_opus_output(500))
    assert by_name["Bash"].calls == 1
    assert by_name["Read"].calls == 1
    assert by_name["Read"].result_tokens > 0


def test_prompts_split_turns_and_text_only_turns_go_to_no_tool(
    tmp_path: Path,
) -> None:
    facts = _main(
        tmp_path,
        [
            prompt("first " + "a" * 300, 0, promptId="p1"),
            assistant("m1", 10),
            prompt("second", 100),
            assistant("m2", 110),
            assistant("m3", 120),
        ],
    )
    assert [p.idx for p in facts.rows.prompts] == [0, 1]
    assert len(facts.rows.prompts[0].text) <= walk.PROMPT_CHARS
    assert facts.rows.prompts[0].prompt_id == "p1"
    assert [t.prompt_idx for t in facts.rows.turns] == [0, 1, 1]
    assert {t.name for t in facts.rows.tools} == {walk.NO_TOOL}


def test_tool_results_and_meta_records_are_not_prompts(tmp_path: Path) -> None:
    facts = _main(
        tmp_path,
        [
            prompt("real", 0),
            prompt("<system-reminder>injected</system-reminder>", 1),
            prompt("hidden", 2, isMeta=True),
            prompt("[Request interrupted by user]", 3),
            prompt("<command-name>/clear</command-name>", 4),
            assistant("m1", 5, blocks=[use("t1", "Bash", command="ls")]),
            result("t1", 6),
        ],
    )
    assert [p.text for p in facts.rows.prompts] == ["real", "/clear"]


def test_agent_call_and_commit_and_final_tag_are_captured(tmp_path: Path) -> None:
    agent = use("ta", "Agent", description="Find x", subagent_type="Explore")
    commit = use("tc", "Bash", command="git -C ~/src/foo commit -m x")
    facts = _main(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 1, blocks=[agent]),
            result("ta", 2, "launched", toolUseResult={"agentId": "abc"}),
            assistant("m2", 3, blocks=[commit]),
            result("tc", 4, "[main 1a2b3c4d] x\n 1 file changed"),
            assistant(
                "m3", 5, blocks=[{"type": "text", "text": "x\nDONE: ok\nNOTE: y"}]
            ),
        ],
    )
    call = facts.rows.agent_calls[0]
    assert (call.tool_use_id, call.agent_id, call.description) == (
        "ta",
        "abc",
        "Find x",
    )
    assert call.subagent_type == "Explore"
    assert facts.rows.commits[0].sha == "1a2b3c4d"
    assert facts.rows.commits[0].repo.endswith("/src/foo")
    assert facts.final_tag == "DONE"


@pytest.mark.parametrize(
    ("text", "tag"),
    [
        ("all good", None),
        ("**NEEDS ACTION:** run it", "NEEDS ACTION"),
        ("RUNNING: tests", "RUNNING"),
    ],
)
def test_final_tag_variants(tmp_path: Path, text: str, tag: str | None) -> None:
    blocks = [{"type": "text", "text": text}]
    facts = _main(tmp_path, [prompt("go", 0), assistant("m1", 1, blocks=blocks)])
    assert facts.final_tag == tag


def test_lever_table_in_a_tool_result_is_kept(tmp_path: Path) -> None:
    table = (
        "## Candidate levers (rule-based)\n\n| category | lever |\n|---|---|\n"
        "| a | b |\n\nafter"
    )
    facts = _main(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 1, blocks=[use("t1", "Bash", command="x")]),
            result("t1", 2, table),
        ],
    )
    assert facts.rows.lever_tables[0][1].splitlines()[-1] == "| a | b |"


def test_activity_intervals_break_on_gaps_over_five_minutes(tmp_path: Path) -> None:
    facts = _main(
        tmp_path,
        [prompt("a", 0), assistant("m1", 60), prompt("b", 1000), assistant("m2", 1100)],
    )
    spans = [(round(e - s)) for s, e in facts.rows.intervals]
    assert spans == [60, 100]
    assert facts.span[1] - facts.span[0] == 1100


def test_subagent_file_reads_meta_and_parent(tmp_path: Path) -> None:
    sub = tmp_path / "proj" / "sess-1" / "subagents" / "agent-abc.jsonl"
    write(sub, [prompt("task", 0), assistant("m1", 1, model="claude-sonnet-5-5")])
    sub.with_suffix(".meta.json").write_text(
        '{"agentType": "Explore", "description": "Find", "toolUseId": "ta"}',
        encoding="utf-8",
    )
    facts = walk.walk_file(sub, tmp_path)
    assert facts.key == "sess-1/agent-abc"
    assert facts.parent_session == "sess-1"
    assert facts.meta["toolUseId"] == "ta"
    assert facts.rows.prompts == []
