"""Element-targeted device driver built on ``adb`` + ``uiautomator dump``."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import tempfile
import time

from python_pkg.android_ui._elements import (
    AmbiguousElementError,
    ElementNotFoundError,
    UiAutomationError,
    UiElement,
    _escape,
    _parse_tree,
)
from python_pkg.android_ui._text_entry import TextEntryMixin

_logger = logging.getLogger(__name__)

_REMOTE_DUMP = "/sdcard/window_dump.xml"

# A tree this small is a partial render, not a real screen. Flutter reports
# only the focused EditText nodes while the soft keyboard is up, so "Connect
# Firebase is absent" and "the dump caught the keyboard" look identical unless
# the node count is taken into account.
_SUSPICIOUSLY_SMALL_TREE = 4


class AndroidUi(TextEntryMixin):
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
