from __future__ import annotations

import pytest

from python_pkg.token_audit import attribute
from python_pkg.token_audit.imagecost import image_cost
from python_pkg.token_audit.model import Session, ToolCall, Turn


def _turn(
    context: int = 0,
    out: int = 0,
    read: int = 0,
    create: int = 0,
    *,
    sidechain: bool = False,
    model: str = "claude-opus-5",
) -> Turn:
    return Turn(
        usage={
            "output_tokens": out,
            "cache_read_input_tokens": read,
            "cache_creation_input_tokens": create,
        },
        context=context,
        model=model,
        is_sidechain=sidechain,
    )


def _session(
    cwd: str | None = "/home/kuhy/p",
    turns: list[Turn] | None = None,
    tools: list[ToolCall] | None = None,
    image_cost_value: float = 0.0,
) -> Session:
    session = Session(session_id="s", path="p", cwd=cwd)
    session.turns = turns or []
    session.tools = tools or []
    session.image_cost = image_cost_value
    return session


def test_totals_sum_each_token_kind() -> None:
    session = _session(turns=[_turn(out=2, read=100), _turn(out=1, read=50)])
    totals, _ = attribute.build([session])
    assert totals.by_kind["output_tokens"] == 3
    assert totals.by_kind["cache_read_input_tokens"] == 150
    assert totals.turns == 2


def test_unknown_cwd_is_labelled() -> None:
    _, axes = attribute.build([_session(cwd=None, turns=[_turn(out=1)])])
    assert "unknown" in axes.project


def test_sidechain_cost_isolated() -> None:
    session = _session(turns=[_turn(out=1, sidechain=True), _turn(out=1)])
    _, axes = attribute.build([session])
    assert axes.sidechain.count == 1
    assert axes.sidechain.total == pytest.approx(5.0)


def test_tool_mcp_and_skill_axes() -> None:
    tools = [
        ToolCall(name="Read", result_tokens=10, path="/a.png"),
        ToolCall(name="Read", result_tokens=5, path="/a.py"),
        ToolCall(name="mcp__aseprite__draw_line", result_tokens=1),
        ToolCall(name="Skill", result_tokens=1, skill="finish"),
    ]
    _, axes = attribute.build([_session(tools=tools)])
    assert axes.tool_tokens["Read"] == 15
    assert axes.tool_calls["Read"] == 2
    assert axes.mcp_calls["aseprite"] == 1
    assert axes.skills["finish"] == 1
    assert axes.images.count == 1
    assert axes.images.total == 10


def test_long_session_threshold() -> None:
    short = _session(turns=[_turn(out=1)])
    long_turns = [_turn(out=1) for _ in range(attribute.LONG_SESSION_TURNS + 1)]
    long = _session(turns=long_turns)
    _, axes = attribute.build([short, long])
    assert axes.long_sessions.count == 1
    assert axes.long_sessions.total == pytest.approx(len(long_turns) * 5.0)


def test_cold_start_only_counted_when_nonzero() -> None:
    cold = _session(turns=[_turn(create=1000)])
    warm = _session(turns=[_turn(read=10, create=5)])
    _, axes = attribute.build([cold, warm])
    assert axes.cold_start.count == 1
    assert axes.cold_start.total == 1000


def test_image_cost_is_accumulated_from_sessions() -> None:
    _, axes = attribute.build([_session(image_cost_value=7.5)])
    assert axes.image_cost == pytest.approx(7.5)


def test_models_axis_tracks_output() -> None:
    session = _session(turns=[_turn(out=4, model="claude-sonnet-5")])
    _, axes = attribute.build([session])
    assert axes.models["claude-sonnet-5"] == 4


def test_reconcile_zero_when_consistent() -> None:
    session = _session(turns=[_turn(out=1)])
    totals, _ = attribute.build([session])
    assert attribute.reconcile(totals, [session]) == pytest.approx(0.0)


def test_reconcile_detects_drift() -> None:
    session = _session(turns=[_turn(out=1)])
    totals, _ = attribute.build([session])
    totals.weighted *= 2
    assert attribute.reconcile(totals, [session]) == pytest.approx(0.5)


def test_reconcile_guards_zero_total() -> None:
    totals = attribute.Totals()
    assert attribute.reconcile(totals, []) == 0.0


# --- imagecost ---------------------------------------------------------------


def _ev_turn(context: int) -> tuple[str, Turn]:
    return ("turn", _turn(context=context))


def _ev_image(tokens: int) -> tuple[str, ToolCall]:
    return ("tool", ToolCall(name="Read", result_tokens=tokens, path="/s.png"))


def test_image_charged_once_per_following_turn() -> None:
    events = [_ev_image(1000), _ev_turn(10), _ev_turn(20), _ev_turn(30)]
    assert image_cost(events) == pytest.approx(300.0)


def test_image_not_charged_for_earlier_turns() -> None:
    events = [_ev_turn(10), _ev_image(1000), _ev_turn(20)]
    assert image_cost(events) == pytest.approx(100.0)


def test_compaction_clears_live_images() -> None:
    # context collapses from 100 to 20 (below the 0.7 ratio) => history dropped
    events = [_ev_image(1000), _ev_turn(100), _ev_turn(20), _ev_turn(30)]
    assert image_cost(events) == pytest.approx(100.0)


def test_growth_below_ratio_does_not_trigger_compaction() -> None:
    events = [_ev_image(1000), _ev_turn(100), _ev_turn(90)]
    assert image_cost(events) == pytest.approx(200.0)


def test_non_image_tools_are_free() -> None:
    events = [
        ("tool", ToolCall(name="Bash", result_tokens=9999, path=None)),
        ("tool", ToolCall(name="Read", result_tokens=9999, path="/a.py")),
        _ev_turn(10),
    ]
    assert image_cost(events) == 0.0


def test_unknown_event_payloads_are_ignored() -> None:
    assert image_cost([("tool", "not a toolcall"), ("turn", "not a turn")]) == 0.0


def test_annotate_sets_session_image_cost() -> None:
    from python_pkg.token_audit import imagecost

    session = _session()
    imagecost.annotate(session, [_ev_image(100), _ev_turn(5)])
    assert session.image_cost == pytest.approx(10.0)
