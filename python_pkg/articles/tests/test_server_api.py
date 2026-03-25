"""Integration tests for the articles C server API."""

from http import HTTPStatus
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from typing import Any
import urllib.parse

import pytest


class _HTTPError(Exception):
    """HTTP error with status code."""

    def __init__(self, code: int) -> None:
        super().__init__(f"HTTP {code}")
        self.code = code


def _req(
    url: str, method: str = "GET", data: dict[str, Any] | bytes | None = None
) -> tuple[int, bytes]:
    """Send an HTTP request and return status code and body."""
    if data is not None and not isinstance(data, bytes | bytearray):
        data = json.dumps(data).encode("utf-8")
    parsed = urllib.parse.urlparse(url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    try:
        headers = {"Content-Type": "application/json"}
        conn.request(method, parsed.path or "/", body=data, headers=headers)
        resp = conn.getresponse()
        body = resp.read()
        status = resp.status
    finally:
        conn.close()
    if status >= 400:
        raise _HTTPError(status)
    return status, body


def _probe_server(host: str, port: int) -> bool:
    """Try a single GET to the server. Return True if it responded."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=0.2)
        try:
            conn.request("GET", "/api/articles")
            conn.getresponse().read()
            return True
        finally:
            conn.close()
    except OSError:
        return False


def _wait_for_server(host: str, port: int, attempts: int = 30) -> None:
    """Poll the server until it responds or attempts are exhausted."""
    for _ in range(attempts):
        if _probe_server(host, port):
            return
        time.sleep(0.05)


def test_crud_roundtrip(tmp_path: Path) -> None:
    """Test full CRUD lifecycle for articles API."""
    # Build C server
    here = Path(__file__).resolve().parent.parent
    make_path = shutil.which("make")
    assert make_path is not None, "make not found in PATH"
    subprocess.run([make_path, "-s", "server_c"], check=True, cwd=str(here))

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        _, port = s.getsockname()
    host = "127.0.0.1"
    base = f"http://{host}:{port}"

    # Isolate storage and start server
    env = os.environ.copy()
    env["ARTICLES_DATA_DIR"] = str(tmp_path)
    env["HOST"] = host
    env["PORT"] = str(port)
    srv = subprocess.Popen(["./server_c"], cwd=str(here), env=env)
    try:
        _wait_for_server(host, port)

        # Create
        code, body = _req(
            base + "/api/articles",
            method="POST",
            data={
                "title": "T1",
                "body": "<p>Hello</p>",
                "thumb": "data:image/png;base64,xyz",
            },
        )
        assert code == HTTPStatus.CREATED
        created = json.loads(body)
        art_id = created["id"]

        # List
        code, body = _req(base + "/api/articles")
        assert code == HTTPStatus.OK
        items = json.loads(body)
        assert any(a["id"] == art_id for a in items)

        # Get one
        code, body = _req(base + f"/api/articles/{art_id}")
        assert code == HTTPStatus.OK
        got = json.loads(body)
        assert got["title"] == "T1"

        # Update
        code, body = _req(
            base + f"/api/articles/{art_id}", method="PUT", data={"title": "T2"}
        )
        assert code == HTTPStatus.OK
        updated = json.loads(body)
        assert updated["title"] == "T2"

        # Delete
        code, _ = _req(base + f"/api/articles/{art_id}", method="DELETE")
        assert code == HTTPStatus.NO_CONTENT

        # Ensure gone
        with pytest.raises(_HTTPError) as exc_info:
            _req(base + f"/api/articles/{art_id}")
        assert exc_info.value.code == HTTPStatus.NOT_FOUND

    finally:
        srv.terminate()
        try:
            srv.wait(timeout=2)
        except subprocess.TimeoutExpired:
            srv.kill()
