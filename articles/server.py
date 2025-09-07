#!/usr/bin/env python3
import json
import os
import random
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Storage helpers

def _data_dir():
    base = os.environ.get("ARTICLES_DATA_DIR") or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(base, exist_ok=True)
    return base


def _data_file():
    return os.path.join(_data_dir(), "articles.json")


def _load():
    fp = _data_file()
    if not os.path.exists(fp):
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(articles):
    with open(_data_file(), "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False)


def _uid():
    return f"{int(__import__('time').time()*1000):x}{random.randrange(1<<20):x}"[:16]


class App(SimpleHTTPRequestHandler):
    # Serve static from the site directory
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)

    # CORS / common headers
    def _headers(self, code=200, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            self._headers(HTTPStatus.NO_CONTENT)
            self.end_headers()
        else:
            super().do_OPTIONS()

    def do_GET(self):
        if self.path.startswith("/api/articles"):
            self._api_get()
        else:
            # Serve static (index.html for root)
            if self.path == "/":
                self.path = "/index.html"
            return super().do_GET()

    def do_POST(self):
        if self.path == "/api/articles":
            self._api_post()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def do_PUT(self):
        if self.path.startswith("/api/articles/"):
            self._api_put()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def do_DELETE(self):
        if self.path.startswith("/api/articles/"):
            self._api_delete()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    # --- API methods ---
    def _read_json(self):
        try:
            ln = int(self.headers.get('Content-Length', 0))
        except Exception:
            ln = 0
        raw = self.rfile.read(ln) if ln > 0 else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _api_get(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        arts = sorted(_load(), key=lambda x: x.get("createdAt", 0), reverse=True)
        if len(parts) == 1:  # /api
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if len(parts) == 2 and parts[1] == "articles":
            self._headers(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(json.dumps(arts).encode("utf-8"))
            return
        # /api/articles/<id>
        if len(parts) == 3 and parts[1] == "articles":
            art = next((a for a in arts if a.get("id") == parts[2]), None)
            if not art:
                self._headers(HTTPStatus.NOT_FOUND)
                self.end_headers()
                return
            self._headers(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(json.dumps(art).encode("utf-8"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _api_post(self):
        data = self._read_json()
        title = (data.get("title") or "Untitled").strip()
        body = data.get("body") or ""
        thumb = data.get("thumb") or ""
        art = {"id": _uid(), "title": title, "body": body, "thumb": thumb, "createdAt": int(__import__('time').time()*1000)}
        arts = _load()
        arts.insert(0, art)
        _save(arts)
        self._headers(HTTPStatus.CREATED)
        self.end_headers()
        self.wfile.write(json.dumps(art).encode("utf-8"))

    def _api_put(self):
        art_id = urlparse(self.path).path.rsplit("/", 1)[-1]
        data = self._read_json()
        arts = _load()
        for i, a in enumerate(arts):
            if a.get("id") == art_id:
                a.update({k: v for k, v in data.items() if k in ("title", "body", "thumb")})
                a["updatedAt"] = int(__import__('time').time()*1000)
                arts[i] = a
                _save(arts)
                self._headers(HTTPStatus.OK)
                self.end_headers()
                self.wfile.write(json.dumps(a).encode("utf-8"))
                return
        self._headers(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def _api_delete(self):
        art_id = urlparse(self.path).path.rsplit("/", 1)[-1]
        arts = _load()
        new_arts = [a for a in arts if a.get("id") != art_id]
        if len(new_arts) == len(arts):
            self._headers(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return
        _save(new_arts)
        self._headers(HTTPStatus.NO_CONTENT)
        self.end_headers()


def serve(host="127.0.0.1", port=8000):
    httpd = HTTPServer((host, port), App)
    print(f"Serving Mini Articles on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def make_server(host="127.0.0.1", port=0):
    httpd = HTTPServer((host, port), App)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    return httpd, th


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    serve(host, port)
