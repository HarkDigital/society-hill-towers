#!/usr/bin/env python3
"""Tiny local sink for the OG beauty-shot capture.

Run it, load the built page with ?dev=1, render, draw #gl to a 2D canvas,
then POST canvas.toDataURL('image/png') as text/plain to
http://127.0.0.1:8123/shot. The decoded PNG lands at brand/og_raw.png.
"""

import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

OUT = Path(__file__).resolve().parent / "og_raw.png"


class Sink(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        data = body.decode("ascii").split(",", 1)[1]
        OUT.write_bytes(base64.b64decode(data))
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"ok")
        print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

    def log_message(self, *a):
        pass


print("og sink on http://127.0.0.1:8123/shot")
HTTPServer(("127.0.0.1", 8123), Sink).serve_forever()
