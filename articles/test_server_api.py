import json
import os
import time
import urllib.request
import urllib.error

SITE_DIR = os.path.join(os.path.dirname(__file__), '..', 'site')
import sys
sys.path.insert(0, SITE_DIR)

from server import make_server  # type: ignore


def _req(url, method="GET", data=None):
    if data is not None and not isinstance(data, (bytes, bytearray)):
        data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read()
        return resp.getcode(), body


def test_crud_roundtrip(tmp_path):
    # Isolate storage
    os.environ["ARTICLES_DATA_DIR"] = str(tmp_path)

    httpd, th = make_server(port=0)
    host, port = httpd.server_address
    base = f"http://{host}:{port}"

    # Create
    code, body = _req(base+"/api/articles", method="POST", data={
        "title": "T1",
        "body": "<p>Hello</p>",
        "thumb": "data:image/png;base64,xyz"
    })
    assert code == 201
    created = json.loads(body)
    art_id = created["id"]

    # List
    code, body = _req(base+"/api/articles")
    assert code == 200
    items = json.loads(body)
    assert any(a["id"] == art_id for a in items)

    # Get one
    code, body = _req(base+f"/api/articles/{art_id}")
    assert code == 200
    got = json.loads(body)
    assert got["title"] == "T1"

    # Update
    code, body = _req(base+f"/api/articles/{art_id}", method="PUT", data={"title": "T2"})
    assert code == 200
    updated = json.loads(body)
    assert updated["title"] == "T2"

    # Delete
    code, _ = _req(base+f"/api/articles/{art_id}", method="DELETE")
    assert code == 204

    # Ensure gone
    try:
        _req(base+f"/api/articles/{art_id}")
        assert False, "Expected 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404

    httpd.shutdown()
    th.join(timeout=2)
