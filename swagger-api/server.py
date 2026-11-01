#!/usr/bin/env python3
"""Serve the Swagger page and forward its calls to the local APIs."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST = "0.0.0.0"
PORT = 8080
GATEWAY = "http://127.0.0.1:4000"
KIKI_TRANSLATE = "http://127.0.0.1:8010/translate"
KIKI_MODELS = {"kiki-tafsiri"}
LFM_MODELS = {
    "lfm3",
    "lfm3-1.7b-base",
    "lfm3-1.7b-fp8",
    "lfm3-vl-2b",
    "lfm3-audio-2b",
    "lfm3-omni-2b",
}
UPSTREAMS = (
    ("/v1/", GATEWAY),
    ("/translate", "http://127.0.0.1:8010"),
)
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_OPTIONS(self):
        self._handle()

    def _handle(self):
        path = urlsplit(self.path).path
        if path == "/kiki/translate":
            self._proxy(KIKI_TRANSLATE)
            return
        if path == "/kiki/chat":
            self._proxy(GATEWAY + "/v1/chat/completions", model="kiki-tafsiri")
            return
        if path == "/kiki/models":
            self._models(KIKI_MODELS)
            return
        if path == "/lfm/models":
            self._models(LFM_MODELS)
            return
        if path.startswith("/lfm/") and path.endswith("/chat"):
            model = path[len("/lfm/") : -len("/chat")].strip("/")
            if model not in LFM_MODELS:
                self._send(404, b'{"detail":"Unknown LFM model"}', "application/json")
                return
            self._proxy(GATEWAY + "/v1/chat/completions", model=model)
            return
        for prefix, origin in UPSTREAMS:
            if path == prefix.rstrip("/") or path.startswith(prefix):
                self._proxy(origin + self.path)
                return
        if self.command != "GET":
            self._send(405, b"Method not allowed", "text/plain; charset=utf-8")
            return
        self._static(path)

    def _proxy(self, url, model=None):
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None
        if model is not None:
            try:
                payload = json.loads(body or b"{}")
            except json.JSONDecodeError:
                self._send(400, b'{"detail":"Request body must be JSON"}', "application/json")
                return
            if not isinstance(payload, dict):
                self._send(400, b'{"detail":"Request body must be a JSON object"}', "application/json")
                return
            payload["model"] = model
            body = json.dumps(payload).encode()
        headers = {}
        for name in ("Authorization", "Content-Type", "Accept"):
            value = self.headers.get(name)
            if value:
                headers[name] = value
        if body is not None and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        request = Request(
            url,
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urlopen(request, timeout=180) as response:
                payload = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "application/json")
        except HTTPError as error:
            payload = error.read()
            status = error.code
            content_type = error.headers.get("Content-Type", "application/json")
        except URLError:
            payload = b'{"detail":"The model service is not reachable"}'
            status = 502
            content_type = "application/json"
        self._send(status, payload, content_type)

    def _models(self, allowed):
        headers = {}
        authorization = self.headers.get("Authorization")
        if authorization:
            headers["Authorization"] = authorization
        request = Request(GATEWAY + "/v1/models", headers=headers, method="GET")
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode())
                status = response.status
        except HTTPError as error:
            self._send(error.code, error.read(), error.headers.get("Content-Type", "application/json"))
            return
        except URLError:
            self._send(502, b'{"detail":"The model service is not reachable"}', "application/json")
            return
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            payload["data"] = [item for item in payload["data"] if item.get("id") in allowed]
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        relative = os.path.normpath(path.lstrip("/"))
        if relative.startswith("..") or relative == "..":
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        full = os.path.join(ROOT, relative)
        if not os.path.isfile(full):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        with open(full, "rb") as handle:
            payload = handle.read()
        content_type = TYPES.get(os.path.splitext(full)[1], "application/octet-stream")
        self._send(200, payload, content_type)

    def _send(self, status, payload, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Swagger on http://{HOST}:{PORT}/")
    server.serve_forever()
