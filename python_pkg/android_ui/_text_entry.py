"""Typing into fields and driving the on-screen keyboard.

Split out of :mod:`python_pkg.android_ui.driver` to keep it under the 250-line
cap. A mixin rather than module-level functions because
``tests/test_driver.py`` calls these as bound attributes of a real driver, and
because they need ``_run``/``dump``/``wait_for`` from the concrete class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import re
import time

from python_pkg.android_ui._elements import (
    ElementNotFoundError,
    UiAutomationError,
    UiElement,
    _escape,
)

# Horizontal slack when re-identifying a field after typing: the keyboard can
# shift a widget vertically, but not sideways, so the left edge stays put.
_SAME_FIELD_X_TOLERANCE_PX = 50


class TextEntryMixin(ABC):
    """The text-entry half of :class:`~python_pkg.android_ui.driver.AndroidUi`."""

    _settle: float

    @abstractmethod
    def _run(self, *args: str, timeout: float = 30.0) -> str:
        """Supplied by the concrete driver: run one adb command."""

    @abstractmethod
    def dump(self, *, retries: int = 4) -> list[UiElement]:
        """Supplied by the concrete driver: read the current UI tree."""

    @abstractmethod
    def wait_for(
        self, query: str, *, timeout: float = 15.0, exact: bool = False
    ) -> UiElement:
        """Supplied by the concrete driver: block until an element appears."""

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
