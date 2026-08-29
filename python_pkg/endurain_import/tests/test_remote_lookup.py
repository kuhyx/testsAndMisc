"""Asking Endurain what it already holds.

A failed lookup must return None, never an empty list: read as "nothing
matches" it would upload a duplicate on every transport hiccup.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import requests

from python_pkg.endurain_import import upload


class _Resp:
    def __init__(self, status: int, payload: object, *, bad_json: bool = False) -> None:
        self.status_code = status
        self._payload = payload
        self._bad_json = bad_json

    def json(self) -> object:
        if self._bad_json:
            message = "not json"
            raise ValueError(message)
        return self._payload


def _client_with_get(
    monkeypatch: pytest.MonkeyPatch, result: object
) -> upload.EndurainClient:
    client = upload.EndurainClient("http://x", "k")

    def _get(*_a: object, **_k: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(client._session, "get", _get)
    return client


def test_recent_start_times_parses_offsets(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_get(
        monkeypatch,
        _Resp(200, [{"start_time": "2026-08-22T23:51:05+02:00"}]),
    )
    times = client.recent_start_times(1)
    assert times is not None
    assert times[0] == datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC)


def test_recent_start_times_treats_naive_as_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client_with_get(
        monkeypatch, _Resp(200, [{"start_time": "2026-08-22T21:51:05"}])
    )
    times = client.recent_start_times(1)
    assert times == [datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC)]


def test_recent_start_times_accepts_zulu(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_get(
        monkeypatch, _Resp(200, [{"start_time": "2026-08-22T21:51:05Z"}])
    )
    times = client.recent_start_times(1)
    assert times == [datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC)]


def test_unparseable_entries_are_dropped_not_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client_with_get(
        monkeypatch,
        _Resp(
            200,
            [
                {"start_time": "nonsense"},
                {"start_time": None},
                {"start_time": ""},
                {"no_start_time": 1},
                "not-a-dict",
                {"start_time": "2026-08-22T21:51:05Z"},
            ],
        ),
    )
    assert client.recent_start_times(1) == [
        datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC)
    ]


def test_auth_failure_is_unknown_not_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """401 must not read as 'no activities exist' -- that would duplicate."""
    client = _client_with_get(monkeypatch, _Resp(401, None))
    assert client.recent_start_times(1) is None


def test_transport_failure_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_get(monkeypatch, requests.ConnectionError("down"))
    assert client.recent_start_times(1) is None


def test_non_json_body_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_get(monkeypatch, _Resp(200, None, bad_json=True))
    assert client.recent_start_times(1) is None


def test_non_list_body_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_get(monkeypatch, _Resp(200, {"detail": "nope"}))
    assert client.recent_start_times(1) is None


def test_already_present_tolerates_recording_skew() -> None:
    """The file said 21:51:04Z; Endurain stored 21:51:05Z. Same run."""
    start = datetime(2026, 8, 22, 21, 51, 4, tzinfo=UTC)
    known = [datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC)]
    assert upload.already_present(start, known)


def test_already_present_rejects_a_different_run() -> None:
    start = datetime(2026, 8, 22, 21, 51, 4, tzinfo=UTC)
    known = [datetime(2026, 8, 22, 19, 0, 0, tzinfo=UTC)]
    assert not upload.already_present(start, known)


def test_tolerance_boundary_is_inclusive() -> None:
    start = datetime(2026, 8, 22, 21, 51, 4, tzinfo=UTC)
    inside = [datetime(2026, 8, 22, 21, 53, 4, tzinfo=UTC)]
    outside = [datetime(2026, 8, 22, 21, 53, 5, tzinfo=UTC)]
    assert upload.already_present(start, inside)
    assert not upload.already_present(start, outside)


def test_already_present_against_nothing_is_false() -> None:
    assert not upload.already_present(datetime(2026, 8, 22, 21, 51, 4, tzinfo=UTC), [])
