"""The state and collaborators the worker's two halves both rely on.

:class:`~python_pkg.wsg_grabber.downloader.Worker` is assembled from two mixins
-- :mod:`._scan` and :mod:`._fetch` -- so that no single module exceeds the
250-line cap. Each half touches bookkeeping the other half owns, so both
inherit from here rather than declaring the same attributes twice.

The annotations carry no values: ``Worker.__init__`` remains the only place
this state is created. The two methods are abstract because ``Worker`` supplies
them; declaring them gives mypy and pylint something real to resolve against,
which a bare mixin does not.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_pkg.wsg_grabber.downloader import WorkerDeps
    from python_pkg.wsg_grabber.models import (
        DownloadEvent,
        JsonResponse,
        ThreadRef,
    )


class WorkerBase(ABC):
    """State and collaborators shared by the worker's two halves."""

    _deps: WorkerDeps
    _pending_threads: list[ThreadRef]
    _catalog_fresh: bool
    _finished_announced: bool

    # Given a real class-level default rather than a bare annotation: _fetch
    # increments it (`self._downloaded += 1`), and pylint only treats an
    # attribute as existing for assignment when there is something to assign
    # to. Worker.__init__ still sets the instance value on construction.
    _downloaded: int = 0

    @abstractmethod
    def _get_json(self, url: str, stamp: str | None = None) -> JsonResponse:
        """Fetch a JSON endpoint, pacing requests and counting the last one."""

    @abstractmethod
    def _publish(self, event: DownloadEvent) -> None:
        """Hand an event to the UI thread."""

    @abstractmethod
    def _wait_for_slot(self) -> None:
        """Block until the polite inter-request delay has elapsed."""
