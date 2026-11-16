"""MCP server over :class:`~python_pkg.android_ui.driver.AndroidUi`, on stdio.

    python3 -m python_pkg.android_ui.mcp_server

Eight tools, one per driver method, adding no behaviour: ``dump``, ``find``,
``tap``, ``type_into``, ``type_into_field``, ``wait_for``, ``scroll_to`` and
``focus``. No screenshot tool, on purpose: an element list is cheaper and can
be asserted on.

Error contract: every :class:`~python_pkg.android_ui.driver.UiAutomationError`
(zero or several matches, a field that did not change, an adb failure) and
every device/display/lease refusal is an ``isError`` result whose message
names the query. Nothing failed is ever returned success-shaped. Typed text is
never echoed back in an error.

Every tool takes optional ``serial`` (default: the one attached device) and
``display`` (default ``"self"``, this session's ``phone_vd.sh`` display; pass
``0`` for the real screen). See :mod:`python_pkg.android_ui._mcp_target`.

Nothing here may write to stdout: it carries the MCP protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from python_pkg.android_ui._mcp_target import connect, redact
from python_pkg.android_ui.driver import UiAutomationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from python_pkg.android_ui.driver import AndroidUi, UiElement

mcp = FastMCP(
    "android-ui",
    instructions=(
        "Drive an Android app by element (text, content-desc, hint, "
        "resource-id), never by coordinates. A query matching 0 or >1 "
        "elements is an error: refine it or pass exact=true. Default display "
        "is this session's virtual display ('self'); pass display=0 for the "
        "real screen."
    ),
)


def _element(element: UiElement) -> dict[str, Any]:
    """Return one element as plain data, bounds and tap centre included."""
    return {
        "label": element.label,
        "text": element.text,
        "content_desc": element.content_desc,
        "hint": element.hint,
        "resource_id": element.resource_id,
        "class_name": element.class_name,
        "bounds": list(element.bounds),
        "center": list(element.center),
        "enabled": element.enabled,
        "focused": element.focused,
    }


def _drive[T](
    command: str,
    serial: str | None,
    display: str | int,
    action: Callable[[AndroidUi], T],
    typed: str = "",
) -> T:
    """Run ``action`` on a resolved driver, turning failures into ToolError."""
    ui = connect(serial, display, command)
    try:
        return action(ui)
    except UiAutomationError as exc:
        raise ToolError(redact(str(exc), typed)) from exc


@mcp.tool
def dump(serial: str | None = None, display: str | int = "self") -> list[str]:
    """List every labelled element on screen, one line each."""
    return _drive("dump", serial, display, lambda ui: [str(e) for e in ui.dump()])


@mcp.tool
def find(
    query: str,
    *,
    exact: bool = False,
    serial: str | None = None,
    display: str | int = "self",
) -> dict[str, Any]:
    """Return the single element matching ``query`` without touching it."""
    return _drive(
        "find", serial, display, lambda ui: _element(ui.find(query, exact=exact))
    )


@mcp.tool
def tap(
    query: str,
    *,
    exact: bool = False,
    timeout: float = 15.0,
    serial: str | None = None,
    display: str | int = "self",
) -> dict[str, Any]:
    """Tap the one element matching ``query``; error on 0 or >1 matches."""
    return _drive(
        "tap",
        serial,
        display,
        lambda ui: _element(ui.tap(query, exact=exact, timeout=timeout)),
    )


@mcp.tool
def type_into(
    query: str,
    text: str,
    *,
    exact: bool = False,
    timeout: float = 15.0,
    serial: str | None = None,
    display: str | int = "self",
) -> str:
    """Type ``text`` into the field matching ``query``; error if it did not change."""
    _drive(
        "type",
        serial,
        display,
        lambda ui: ui.type_into(query, text, exact=exact, timeout=timeout),
        typed=text,
    )
    return f"typed {len(text)} character(s) into {query!r} and verified"


@mcp.tool
def type_into_field(
    index: int,
    text: str,
    serial: str | None = None,
    display: str | int = "self",
) -> str:
    """Type into the ``index``-th editable field (top to bottom); verified."""
    _drive(
        "type",
        serial,
        display,
        lambda ui: ui.type_into_field(index, text),
        typed=text,
    )
    return f"typed {len(text)} character(s) into editable field #{index} and verified"


@mcp.tool
def wait_for(
    query: str,
    *,
    timeout: float = 15.0,
    exact: bool = False,
    serial: str | None = None,
    display: str | int = "self",
) -> dict[str, Any]:
    """Poll until ``query`` matches exactly one element, or error on timeout."""
    return _drive(
        "wait",
        serial,
        display,
        lambda ui: _element(ui.wait_for(query, timeout=timeout, exact=exact)),
    )


@mcp.tool
def scroll_to(
    query: str,
    *,
    exact: bool = False,
    max_swipes: int = 8,
    serial: str | None = None,
    display: str | int = "self",
) -> dict[str, Any]:
    """Swipe up until ``query`` is on screen, then return it."""
    return _drive(
        "scroll-to",
        serial,
        display,
        lambda ui: _element(ui.scroll_to(query, exact=exact, max_swipes=max_swipes)),
    )


@mcp.tool
def focus(serial: str | None = None, display: str | int = "self") -> str:
    """Return the focused window (package/activity)."""
    return _drive("focus", serial, display, lambda ui: ui.current_focus())


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
