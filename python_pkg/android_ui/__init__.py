"""Element-targeted Android UI automation over adb, for agents and scripts.

Drives a real device by *identity* (text, content-desc, resource-id) rather
than by pixel coordinates read off a screenshot. Coordinate tapping breaks in
three ways this package exists to remove, all of them observed on 2026-08-10
while verifying the workout app's Firebase restore:

* **A mis-tap is silent.** A tap at ``(540, 1705)`` aimed at a password field
  landed with the field unfocused; the typed password went nowhere and nothing
  errored. :func:`~python_pkg.android_ui.driver.AndroidUi.type_into` verifies
  the field's text actually changed and raises when it did not.
* **Layout shifts invalidate coordinates.** Opening the soft keyboard moved a
  field from y=1572 to y=1319, so a coordinate captured one step earlier was
  already wrong. Every action re-reads the tree immediately before acting.
* **Screenshots are expensive and unassertable.** A full-page PNG per step
  costs far more than the element list it stands in for, and cannot be
  grepped. :meth:`~python_pkg.android_ui.driver.AndroidUi.dump` returns text.

Two device quirks are handled rather than documented, because both produced
false results before they were understood:

* ``uiautomator dump`` returns ONLY the ``EditText`` nodes while a Flutter text
  field holds focus — the button you are about to tap is simply missing, and it
  stays missing across retries, so a naive retry loop never converges.
* ``KEYCODE_BACK`` is treated by Flutter as a route pop, not a keyboard
  dismiss: it navigated out of Settings and discarded typed input, twice.

See :mod:`python_pkg.android_ui.driver` for the API and
:mod:`python_pkg.android_ui.cli` for the command line.
"""

from __future__ import annotations

from python_pkg.android_ui.driver import (
    AmbiguousElementError,
    AndroidUi,
    ElementNotFoundError,
    UiAutomationError,
    UiElement,
)

__all__ = [
    "AmbiguousElementError",
    "AndroidUi",
    "ElementNotFoundError",
    "UiAutomationError",
    "UiElement",
]
