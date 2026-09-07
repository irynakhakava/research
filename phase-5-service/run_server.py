#!/usr/bin/env python3
"""Фаза 5: HTTP API GET /health, POST /search, POST /ask.

  python phase-5-service/run_server.py
  curl -s localhost:8080/health
  curl -s localhost:8080/search -H 'Content-Type: application/json' \\
    -d '{"question":"Как откатить payments в staging?"}'
  curl -s localhost:8080/ask -H 'Content-Type: application/json' \\
    -d '{"question":"Как откатить payments в staging?"}'
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-3-generation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-2-retrieval"))

from service.app import do_ask, do_search, health_payload, load_context
from service.config import load_config
from service.loggingutil import new_trace_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5: HTTP /search + /ask")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument(
        "--embed-backend",
        choices=["sentence_transformers", "hash"],
        default=None,
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    try:
        ctx = load_context(cfg, embed_backend=args.embed_backend)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    server_cfg = dict(cfg.get("server") or {})
    host = args.host or str(server_cfg.get("host", "127.0.0.1"))
    port = args.port if args.port is not None else int(server_cfg.get("port", 8080))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *log_args: Any) -> None:
            return

        def _json(self, code: int, payload: dict) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _trace(self) -> str:
            return new_trace_id(self.headers.get("X-Trace-Id"))

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/health", "/"}:
                self._json(200, health_payload())
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid json", "trace_id": self._trace()})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "json object required", "trace_id": self._trace()})
                return
            trace_id = self._trace()
            try:
                if path == "/search":
                    code, payload = do_search(ctx, body, trace_id=trace_id)
                elif path == "/ask":
                    code, payload = do_ask(ctx, body, trace_id=trace_id)
                else:
                    self._json(404, {"error": "not found", "trace_id": trace_id})
                    return
            except Exception as exc:
                self._json(500, {"error": str(exc), "trace_id": trace_id})
                return
            self._json(code, payload)

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"nordledger-doc-search http://{host}:{port}  /health /search /ask", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
