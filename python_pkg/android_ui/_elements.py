"""The element and error types the UI driver works in, and the XML parser.

Split out of :mod:`python_pkg.android_ui.driver` to keep it under the 250-line
cap. ``AndroidUi`` stays there because that is the name the tests patch;
everything here is re-imported by ``driver`` so the package's public re-exports
in ``__init__`` are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from defusedxml.ElementTree import ParseError, fromstring

_logger = logging.getLogger(__name__)

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class UiAutomationError(RuntimeError):
    """Base class for every failure this package reports."""


class ElementNotFoundError(UiAutomationError):
    """No element matched the query."""


class AmbiguousElementError(UiAutomationError):
    """More than one element matched, so acting would be a coin flip."""


@dataclass(frozen=True)
class UiElement:
    """One node from the accessibility tree."""

    text: str
    content_desc: str
    resource_id: str
    class_name: str
    bounds: tuple[int, int, int, int]
    enabled: bool
    focused: bool

    @property
    def label(self) -> str:
        """The best human-facing name for this element."""
        return self.text or self.content_desc or self.resource_id

    @property
    def center(self) -> tuple[int, int]:
        """Tap point: the centre of the element's CURRENT bounds."""
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)

    def matches(self, query: str, *, exact: bool = False) -> bool:
        """Return True if ``query`` names this element."""
        haystacks = (self.text, self.content_desc, self.resource_id)
        if exact:
            return any(h == query for h in haystacks)
        return any(query.lower() in h.lower() for h in haystacks if h)

    def __str__(self) -> str:
        """Return a one-line description naming the element and its centre."""
        cls = self.class_name.rsplit(".", 1)[-1]
        x, y = self.center
        return f"{self.label!r} <{cls}> at ({x},{y})"


def _escape(text: str) -> str:
    r"""Escape text for ``adb shell input text``.

    Backslash is escaped FIRST and excluded from the loop below. Escaping it
    inside the loop double-escapes every backslash the loop itself just added
    (``&`` -> ``\\&`` -> ``\\\\&``), which silently types the wrong password.
    """
    out = text.replace("\\", "\\\\")
    out = out.replace("%", "%%").replace(" ", "%s")
    for char in "()<>|;&*~\"'`$":
        out = out.replace(char, "\\" + char)
    return out


def _parse_tree(xml: str) -> list[UiElement]:
    """Return every labelled node in an accessibility-tree dump."""
    try:
        root = fromstring(xml)
    except ParseError as exc:
        _logger.warning(
            "UI dump is not valid XML (%s) — treating it as an empty screen; "
            "this is usually a snapshot taken mid-animation",
            exc,
        )
        return []

    elements: list[UiElement] = []
    for node in root.iter("node"):
        bounds = _BOUNDS_RE.match(node.get("bounds", ""))
        if bounds is None:
            continue
        text = node.get("text", "")
        desc = node.get("content-desc", "")
        res = node.get("resource-id", "")
        cls = node.get("class", "")
        # An EMPTY text field has no text, content-desc or resource-id, so a
        # "must be labelled" filter drops it -- and an empty field is exactly
        # the thing a caller needs to find in order to type into it. Keep every
        # editable node regardless of label.
        if not (text or desc or res or cls.endswith("EditText")):
            continue
        elements.append(
            UiElement(
                text=text,
                content_desc=desc,
                resource_id=res,
                class_name=cls,
                bounds=(
                    int(bounds.group(1)),
                    int(bounds.group(2)),
                    int(bounds.group(3)),
                    int(bounds.group(4)),
                ),
                enabled=node.get("enabled") == "true",
                focused=node.get("focused") == "true",
            )
        )
    return elements
