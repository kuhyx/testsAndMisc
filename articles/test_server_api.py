import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request


def _req(url, method="GET", data=None):
    if data is not None and not isinstance(data, (bytes, bytearray)):
        data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read()
        return resp.getcode(), body


def test_crud_roundtrip(tmp_path):
    # Build C server
    here = Path(__file__).resolve().parent
    subprocess.run(["make", "-s", "server_c"], check=True, cwd=str(here))

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
        # wait briefly for server to be ready
        for _ in range(30):
            try:
                with urllib.request.urlopen(
                    base + "/api/articles", timeout=0.2
                ) as resp:
                    resp.read()
                    break
            except Exception:
                time.sleep(0.05)

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
        assert code == 201
        created = json.loads(body)
        art_id = created["id"]

        # List
        code, body = _req(base + "/api/articles")
        assert code == 200
        items = json.loads(body)
        assert any(a["id"] == art_id for a in items)

        # Get one
        code, body = _req(base + f"/api/articles/{art_id}")
        assert code == 200
        got = json.loads(body)
        assert got["title"] == "T1"

        # Update
        code, body = _req(
            base + f"/api/articles/{art_id}", method="PUT", data={"title": "T2"}
        )
        assert code == 200
        updated = json.loads(body)
        assert updated["title"] == "T2"

        # Delete
        code, _ = _req(base + f"/api/articles/{art_id}", method="DELETE")
        assert code == 204

        # Ensure gone
        try:
            _req(base + f"/api/articles/{art_id}")
            msg = "Expected 404"
            raise AssertionError(msg)
        except urllib.error.HTTPError as e:
            assert e.code == 404

    finally:
        srv.terminate()
        try:
            srv.wait(timeout=2)
        except Exception:
            srv.kill()
