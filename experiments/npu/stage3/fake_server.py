#!/usr/bin/env python3
"""Stand-in for the OpenAI completions endpoint, for offline runner checks.

No model, no device. Each completion sleeps in proportion to the requested
tokens, answers with filler text, and logs every prompt's SHA256 so a check can
compare what two runs sent. ``--no-details`` drops
``usage.prompt_tokens_details`` to exercise the runner's ``null`` path.
"""

from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
import uuid

LOCK = threading.Lock()


def make_handler(args):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _json(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path.startswith("/v1/models"):
                return self._json(200, {"data": [{"id": "fake-model"}]})
            if self.path.startswith("/health"):
                return self._json(200, {})
            self._json(404, {})

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode())
            prompt = req["prompt"]
            max_t = int(req["max_tokens"])
            rid = f"cmpl-{uuid.uuid4().hex[:16]}"
            with LOCK, open(args.log, "a") as fh:
                fh.write(json.dumps({"id": rid, "t": time.time(),
                                     "sha": hashlib.sha256(prompt.encode()).hexdigest(),
                                     "max_tokens": max_t}) + "\n")
            usage = {"prompt_tokens": len(prompt.split()), "completion_tokens": max_t,
                     "total_tokens": len(prompt.split()) + max_t}
            if not args.no_details:
                usage["prompt_tokens_details"] = {"cached_tokens": 0}
            time.sleep(args.prefill_s)
            if not req.get("stream"):
                time.sleep(args.per_token_s * max_t)
                return self._json(200, {"id": rid, "choices": [{"text": " w" * max_t}],
                                        "usage": usage})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for _ in range(max_t):
                time.sleep(args.per_token_s)
                chunk = {"id": rid, "choices": [{"text": " w"}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(f"data: {json.dumps({'id': rid, 'choices': [], 'usage': usage})}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    return H


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--no-details", action="store_true")
    ap.add_argument("--prefill-s", type=float, default=0.005)
    ap.add_argument("--per-token-s", type=float, default=0.0005)
    args = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
