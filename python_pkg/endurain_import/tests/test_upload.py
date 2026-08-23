"""Upload outcome classification.

The distinction that matters: a definite rejection may be retried/staged, an
ambiguous one may NOT, because Endurain does not deduplicate and the activity
may already have been committed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from python_pkg.endurain_import.upload import EndurainClient, Outcome


class _FakeResponse:
    def __init__(self, status: int, body: object = None) -> None:
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self) -> object:
        if self._body is None:
            message = "no json"
            raise ValueError(message)
        return self._body


def _client_with(monkeypatch: pytest.MonkeyPatch, outcome: object) -> EndurainClient:
    client = EndurainClient("http://x", "k")

    def _post(*_args: object, **_kwargs: object) -> object:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client._session, "post", _post)
    return client


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "RunnerUp_ts_Running.tcx"
    path.write_text("<xml/>")
    return path


def test_success_extracts_activity_id(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(201, {"id": 42}))
    result = client.upload(sample)
    assert result.outcome is Outcome.OK
    assert result.activity_id == 42


def test_success_without_parsable_body(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(200))
    result = client.upload(sample)
    assert result.outcome is Outcome.OK
    assert result.activity_id is None


def test_bare_integer_body_is_an_id(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(200, 9))
    assert client.upload(sample).activity_id == 9


def test_client_error_is_rejected(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(400, {"detail": "bad"}))
    assert client.upload(sample).outcome is Outcome.REJECTED


def test_server_error_is_ambiguous(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    """5xx may mean the activity WAS created; retrying could duplicate it."""
    client = _client_with(monkeypatch, _FakeResponse(503, {}))
    assert client.upload(sample).outcome is Outcome.AMBIGUOUS


def test_transport_failure_is_ambiguous(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, requests.Timeout("timed out"))
    assert client.upload(sample).outcome is Outcome.AMBIGUOUS


def test_api_key_header_is_set() -> None:
    """Endurain's OpenAPI schema mislabels this; X-API-Key is correct."""
    client = EndurainClient("http://x/", "secret")
    assert client._session.headers["X-API-Key"] == "secret"


def test_about_returns_parsed_body(monkeypatch: pytest.MonkeyPatch) -> None:
    client = EndurainClient("http://x", "k")

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"version": "0.19.0"}

    monkeypatch.setattr(client._session, "get", lambda *_a, **_k: _Resp())
    assert client.about() == {"version": "0.19.0"}


def test_activity_id_ignores_non_integer_fields(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(200, {"id": "not-an-int"}))
    assert client.upload(sample).activity_id is None


def test_activity_id_from_alternate_key(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(200, {"activity_id": 12}))
    assert client.upload(sample).activity_id == 12


def test_activity_id_none_for_list_body(
    monkeypatch: pytest.MonkeyPatch, sample: Path
) -> None:
    client = _client_with(monkeypatch, _FakeResponse(200, ["a"]))
    assert client.upload(sample).activity_id is None
