"""``scroll_to``: bring a widget that is outside the viewport on screen."""

from __future__ import annotations

from abc import ABC, abstractmethod
import time

from python_pkg.android_ui._elements import ElementNotFoundError, UiElement

_SWIPE_MS = "350"
# Swipe through the middle 40% of the screen: far enough to move a page, short
# enough that Flutter does not turn it into a fling that overshoots the target.
_FROM_FRAC = 0.7
_TO_FRAC = 0.3


def _snapshot(elements: list[UiElement]) -> list[tuple[str, tuple[int, ...]]]:
    """Reduce a tree to what changes when a list scrolls."""
    return [(e.label, e.bounds) for e in elements]


class ScrollMixin(ABC):
    """The scrolling part of :class:`~python_pkg.android_ui.driver.AndroidUi`."""

    _settle: float

    @abstractmethod
    def _input(self, *args: str) -> str:
        """Supplied by the concrete driver: ``input`` on the driven display."""

    @abstractmethod
    def dump(self, *, retries: int = 4) -> list[UiElement]:
        """Supplied by the concrete driver: read the current UI tree."""

    @abstractmethod
    def find(self, query: str, *, exact: bool = False) -> UiElement:
        """Supplied by the concrete driver: the single match, or raise."""

    def scroll_to(
        self, query: str, *, exact: bool = False, max_swipes: int = 8
    ) -> UiElement:
        """Swipe up until ``query`` matches exactly one element, then return it.

        A widget outside the viewport is not in the accessibility tree, so
        ``find`` reports it missing. Stops early, naming the query, when a swipe
        leaves the screen unchanged (the end of the list) rather than spinning
        for ``max_swipes`` swipes. Ambiguity raises, as it does for ``find``.
        """
        elements = self.dump()
        for _ in range(max_swipes):
            if any(e.matches(query, exact=exact) for e in elements):
                return self.find(query, exact=exact)
            width = max((e.bounds[2] for e in elements), default=0)
            height = max((e.bounds[3] for e in elements), default=0)
            x = str(width // 2)
            self._input(
                "swipe",
                x,
                str(int(height * _FROM_FRAC)),
                x,
                str(int(height * _TO_FRAC)),
                _SWIPE_MS,
            )
            time.sleep(self._settle)
            after = self.dump()
            if _snapshot(after) == _snapshot(elements):
                break
            elements = after
        if any(e.matches(query, exact=exact) for e in elements):
            return self.find(query, exact=exact)
        msg = f"scrolled looking for {query!r} but it never appeared"
        raise ElementNotFoundError(msg)
