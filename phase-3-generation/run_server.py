#!/usr/bin/env python3
"""Минимальный HTTP POST /ask (stdlib). Предпочтительно: phase-5-service/run_server.py.

  python phase-3-generation/run_server.py
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-2-retrieval"))

from generation.ask import ask
from generation.citations import load_document_paths, load_source_locations
from generation.config import load_config
from retrieval.embedders import create_embedder
from retrieval.index import load_index


def _build_context(cfg_path: Path | None):
    cfg = load_config(cfg_path)
    index = load_index(cfg["index_dir"])
    embedder = create_embedder(dict(cfg["embeddings"]))
    return cfg, index, embedder


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: HTTP /ask")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    try:
        cfg, index, embedder = _build_context(args.config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    retrieve_cfg = dict(cfg.get("retrieve") or {})
    gen_cfg = dict(cfg.get("generation") or {})
    server_cfg = dict(cfg.get("server") or {})
    host = args.host or str(server_cfg.get("host", "127.0.0.1"))
    port = args.port if args.port is not None else int(server_cfg.get("port", 8080))

    docs = load_document_paths(cfg["documents_path"])
    locs = load_source_locations(cfg["catalog_path"])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *log_args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % log_args))

        def _json(self, code: int, payload: dict) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/health", "/"}:
                self._json(200, {"ok": True, "endpoints": ["/ask", "/health"]})
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/ask":
                self._json(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid json"})
                return
            question = str(body.get("question") or "").strip()
            if not question:
                self._json(400, {"error": "question is required"})
                return
            try:
                resp = ask(
                    index,
                    embedder,
                    question,
                    documents_by_id=docs,
                    locations=locs,
                    mode=str(body.get("mode") or retrieve_cfg.get("mode", "hybrid")),
                    top_k=int(body.get("top_k") or retrieve_cfg.get("top_k", 5)),
                    candidate_k=int(retrieve_cfg.get("candidate_k", 20)),
                    rrf_k=int(retrieve_cfg.get("rrf_k", 60)),
                    team=body.get("team"),
                    acl=body.get("acl"),
                    priority=body.get("priority"),
                    source_id=body.get("source_id"),
                    generation_backend=str(gen_cfg.get("backend", "extractive")),
                    generation_model=str(gen_cfg.get("model_name", "extractive")),
                    max_context_chunks=int(gen_cfg.get("max_context_chunks", 4)),
                    min_dense_score=float(gen_cfg.get("min_dense_score", 0.28)),
                    nearest_links=int(gen_cfg.get("nearest_links", 3)),
                    quote_chars=int(gen_cfg.get("quote_chars", 280)),
                    openai_base_url=str(
                        gen_cfg.get("openai_base_url", "https://api.openai.com/v1")
                    ),
                )
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            self._json(200, resp.to_dict())

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"POST /ask on http://{host}:{port}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
