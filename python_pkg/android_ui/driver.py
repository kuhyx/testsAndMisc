"""Element-targeted device driver built on ``adb`` + ``uiautomator dump``."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re
import subprocess
import tempfile
import time

from defusedxml.ElementTree import ParseError, fromstring

_logger = logging.getLogger(__name__)

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_REMOTE_DUMP = "/sdcard/window_dump.xml"

# A tree this small is a partial render, not a real screen. Flutter reports
# only the focused EditText nodes while the soft keyboard is up, so "Connect
# Firebase is absent" and "the dump caught the keyboard" look identical unless
# the node count is taken into account.
_SUSPICIOUSLY_SMALL_TREE = 4

# Horizontal slack when re-identifying a field after typing: the keyboard can
# shift a widget vertically, but not sideways, so the left edge stays put.
_SAME_FIELD_X_TOLERANCE_PX = 50


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


class AndroidUi:
    """Drives one device. Every action re-reads the tree before acting."""

    def __init__(
        self,
        serial: str | None = None,
        *,
        adb: str = "adb",
        settle_seconds: float = 0.4,
    ) -> None:
        """Create a driver. ``serial`` targets one of several devices."""
        self._adb = adb
        self._serial = serial
        self._settle = settle_seconds

    def _run(self, *args: str, timeout: float = 30.0) -> str:
        """Run an adb command, returning stdout."""
        cmd = [self._adb]
        if self._serial:
            cmd += ["-s", self._serial]
        cmd += list(args)
        try:
            done = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            msg = f"adb timed out after {timeout}s: {' '.join(args)}"
            raise UiAutomationError(msg) from exc
        if done.returncode != 0:
            msg = (
                f"adb failed ({done.returncode}): {' '.join(args)}\n"
                f"{done.stderr.strip()}"
            )
            raise UiAutomationError(msg)
        return done.stdout

    # ── Reading the screen ────────────────────────────────────────────────

    def dump(self, *, retries: int = 4) -> list[UiElement]:
        """Return every labelled element currently on screen.

        Retries while the tree looks partial. ``uiautomator`` returns an empty
        or truncated document mid-animation, and a caller that trusts the first
        answer reports "element not found" for something plainly on screen.
        """
        best: list[UiElement] = []
        for attempt in range(retries):
            elements = self._dump_once()
            if len(elements) > len(best):
                best = elements
            if len(elements) > _SUSPICIOUSLY_SMALL_TREE:
                return elements
            _logger.debug(
                "dump attempt %d returned %d node(s) — retrying, this is "
                "usually an animation or an open keyboard",
                attempt + 1,
                len(elements),
            )
            time.sleep(self._settle * (attempt + 1))
        return best

    def _dump_once(self) -> list[UiElement]:
        """Pull one accessibility-tree snapshot."""
        self._run("shell", "uiautomator", "dump", _REMOTE_DUMP, timeout=45.0)
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "ui.xml"
            self._run("pull", _REMOTE_DUMP, str(local), timeout=45.0)
            try:
                xml = local.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                msg = f"could not read the pulled UI dump: {exc}"
                raise UiAutomationError(msg) from exc
        return _parse_tree(xml)

    def find_all(self, query: str, *, exact: bool = False) -> list[UiElement]:
        """Return every element matching ``query``."""
        return [e for e in self.dump() if e.matches(query, exact=exact)]

    def find(self, query: str, *, exact: bool = False) -> UiElement:
        """Return the single element matching ``query``.

        Zero or several matches raise. An ambiguous query silently acting on
        the first match is how a script taps the wrong thing and reports
        success.
        """
        matches = self.find_all(query, exact=exact)
        if not matches:
            visible = ", ".join(sorted({e.label for e in self.dump() if e.label}))
            msg = (
                f"no element matches {query!r}. On screen now: "
                f"{visible or '(nothing labelled — the tree may be partial)'}"
            )
            raise ElementNotFoundError(msg)
        if len(matches) > 1:
            listed = "; ".join(str(m) for m in matches)
            msg = f"{len(matches)} elements match {query!r}: {listed}"
            raise AmbiguousElementError(msg)
        return matches[0]

    def _clear_focused_field(self, length: int) -> None:
        """Empty the focused field: select-all, then delete."""
        if length == 0:
            return
        # KEYCODE_MOVE_END (123) then a run of deletes is more reliable across
        # IMEs than CTRL+A, which not every keyboard honours.
        self._run("shell", "input", "keyevent", "123")
        for _ in range(length + 2):
            self._run("shell", "input", "keyevent", "67")
        time.sleep(self._settle)

    def editable_fields(self) -> list[UiElement]:
        """Return every editable field on screen, in top-to-bottom order.

        An EMPTY text field carries no text, content-desc or resource-id, so
        there is nothing to name it by — yet it is precisely the element a
        caller needs to address in order to fill it in. Ordering by position
        gives a stable handle ("the second field in the sync form") that does
        not depend on a label the widget never had.
        """
        fields = [e for e in self.dump() if e.class_name.endswith("EditText")]
        return sorted(fields, key=lambda e: (e.bounds[1], e.bounds[0]))

    def type_into_field(self, index: int, text: str) -> None:
        """Type ``text`` into the ``index``-th editable field on screen.

        Verifies the field changed, exactly like :meth:`type_into`.
        """
        fields = self.editable_fields()
        if index >= len(fields):
            msg = f"asked for editable field #{index} but the screen has {len(fields)}"
            raise ElementNotFoundError(msg)
        target = fields[index]
        before = target.text
        x, y = target.center
        self._run("shell", "input", "tap", str(x), str(y))
        time.sleep(max(self._settle, 0.8))
        # REPLACE, don't append. `input text` inserts at the cursor, so typing
        # into a field that already holds something silently concatenates --
        # producing e.g. "old@example.comnew@example.com", which is accepted by
        # the widget, passes a "did the text change?" check, and is wrong.
        self._clear_focused_field(len(before))
        self._run("shell", "input", "text", _escape(text))
        time.sleep(self._settle)
        after = self.editable_fields()
        changed = any(
            f.text != before
            and abs(f.bounds[0] - target.bounds[0]) < _SAME_FIELD_X_TOLERANCE_PX
            for f in after
        )
        if not changed:
            msg = (
                f"typed {len(text)} character(s) into editable field #{index} "
                f"but its contents did not change — the tap did not focus it"
            )
            raise UiAutomationError(msg)

    def wait_for(
        self, query: str, *, timeout: float = 15.0, exact: bool = False
    ) -> UiElement:
        """Poll until ``query`` matches exactly one element, or time out."""
        deadline = time.monotonic() + timeout
        last: UiAutomationError | None = None
        while time.monotonic() < deadline:
            try:
                return self.find(query, exact=exact)
            except UiAutomationError as exc:
                last = exc
            time.sleep(self._settle)
        msg = f"waited {timeout}s for {query!r}: {last}"
        raise ElementNotFoundError(msg)

    # ── Acting ────────────────────────────────────────────────────────────

    def tap(
        self, query: str, *, exact: bool = False, timeout: float = 15.0
    ) -> UiElement:
        """Tap the element matching ``query``, resolved fresh at tap time."""
        element = self.wait_for(query, timeout=timeout, exact=exact)
        # The tree reports a widget's LAID-OUT position even when the soft
        # keyboard is drawn over it, so tapping blind lands on a letter key and
        # reports success. Close the keyboard first rather than guessing.
        if self.keyboard_is_up():
            self.dismiss_keyboard()
            element = self.wait_for(query, timeout=timeout, exact=exact)
        x, y = element.center
        self._run("shell", "input", "tap", str(x), str(y))
        time.sleep(self._settle)
        return element

    def type_into(
        self,
        query: str,
        text: str,
        *,
        exact: bool = False,
        timeout: float = 15.0,
    ) -> None:
        """Focus the field matching ``query``, type ``text``, and verify it.

        Raises when the field's contents did not change. Typing into an
        unfocused field is silent on the device: the keystrokes go nowhere and
        the next screenshot simply shows an empty box.
        """
        element = self.wait_for(query, timeout=timeout, exact=exact)
        before = element.text
        x, y = element.center
        self._run("shell", "input", "tap", str(x), str(y))
        # The field has to actually take focus before keystrokes mean anything.
        time.sleep(max(self._settle, 0.8))
        self._run("shell", "input", "text", _escape(text))
        time.sleep(self._settle)

        for candidate in self.dump():
            same = candidate.bounds == element.bounds or candidate.matches(
                query, exact=exact
            )
            if same and candidate.text != before:
                return
        # A password field renders as bullets, so compare length, not content.
        msg = (
            f"typed {len(text)} character(s) into {query!r} but its contents "
            f"did not change — the tap probably did not focus the field"
        )
        raise UiAutomationError(msg)

    def dismiss_keyboard(self) -> None:
        """Close the soft keyboard WITHOUT popping the current route.

        ``KEYCODE_BACK`` is the obvious way and the wrong one: Flutter treats
        it as a route pop, so it navigates out of the screen and discards
        anything typed. ``KEYCODE_ESCAPE`` leaves the route alone but does not
        close every IME (Gboard ignores it), and a keyboard that stays up hides
        the button you are about to tap -- so the tap lands on a key instead,
        silently doing nothing useful.

        So: ask the IME to hide, verify with ``dumpsys input_method``, and only
        then report success. Raises if the keyboard is still up, because
        "tapped a letter key" is indistinguishable from "tapped the button"
        unless somebody checks.
        """
        for keyevent in ("111", "4"):
            if not self.keyboard_is_up():
                return
            self._run("shell", "input", "keyevent", keyevent)
            time.sleep(max(self._settle, 0.6))
        if self.keyboard_is_up():
            msg = (
                "the soft keyboard is still covering the screen after ESCAPE "
                "and BACK — any tap below it will hit a key, not your target"
            )
            raise UiAutomationError(msg)

    def keyboard_is_up(self) -> bool:
        """Return True while the soft keyboard is shown.

        Without this, a caller cannot tell "the button is absent" from "the
        button is behind the keyboard", and the accessibility tree reports the
        button's laid-out position either way.
        """
        out = self._run("shell", "dumpsys", "input_method")
        match = re.search(r"mInputShown=(\w+)", out)
        return match is not None and match.group(1) == "true"

    def current_focus(self) -> str:
        """Return the focused window, for asserting which screen is up."""
        out = self._run("shell", "dumpsys", "window")
        match = re.search(r"mCurrentFocus=\S+ \S+ (\S+)}", out)
        return match.group(1) if match else ""


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
