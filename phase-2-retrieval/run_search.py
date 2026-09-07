#!/usr/bin/env python3
"""Фаза 2 · пункт 3: поиск по вопросу → top-k чанки.

Примеры:
  python phase-2-retrieval/run_search.py "Как откатить payments в staging?"
  python phase-2-retrieval/run_search.py "CrashLoop payments" --mode hybrid --top-k 5
  python phase-2-retrieval/run_search.py "rollback" --team platform
  python phase-2-retrieval/run_search.py "airflow" --mode bm25 --backend hash
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval.config import REPO_ROOT, load_config
from retrieval.embedders import create_embedder
from retrieval.index import load_index
from retrieval.retrieve import search


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2.3: hybrid search")
    parser.add_argument("query", help="Вопрос на естественном языке")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--mode",
        choices=["hybrid", "dense", "bm25"],
        default=None,
    )
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--acl", default=None)
    parser.add_argument("--priority", default=None)
    parser.add_argument("--source-id", default=None)
    parser.add_argument(
        "--backend",
        choices=["sentence_transformers", "hash"],
        default=None,
        help="Embedder для query (должен совпадать с dim индекса для dense/hybrid)",
    )
    parser.add_argument(
        "--text-chars",
        type=int,
        default=280,
        help="Сколько символов текста чанка печатать",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    retrieve_cfg = dict(cfg.get("retrieve") or {})
    mode = args.mode or str(retrieve_cfg.get("mode", "hybrid"))
    top_k = args.top_k if args.top_k is not None else int(retrieve_cfg.get("top_k", 5))
    rrf_k = int(retrieve_cfg.get("rrf_k", 60))
    candidate_k = int(retrieve_cfg.get("candidate_k", 20))

    index_dir = cfg["index_dir"]
    if not (index_dir / "index_meta.json").exists():
        print(f"ERROR: index not found at {index_dir}", file=sys.stderr)
        print("Run: python phase-2-retrieval/run_index.py", file=sys.stderr)
        return 1

    index = load_index(index_dir)
    emb_cfg = dict(cfg["embeddings"])
    if args.backend:
        emb_cfg["backend"] = args.backend

    # hash backend only works if index dim matches hash dim (64)
    if emb_cfg["backend"] == "hash" and index.vectors.shape[1] != 64:
        print(
            f"ERROR: hash embedder dim=64 but index dim={index.vectors.shape[1]}. "
            "Use sentence_transformers (default) for e5 index.",
            file=sys.stderr,
        )
        return 1

    try:
        embedder = create_embedder(emb_cfg)
    except ImportError as exc:
        print(f"ERROR: cannot load embedder: {exc}", file=sys.stderr)
        return 1

    if mode in {"dense", "hybrid"} and embedder.dim != index.vectors.shape[1]:
        print(
            f"ERROR: query embedder dim={embedder.dim} != index dim={index.vectors.shape[1]}",
            file=sys.stderr,
        )
        return 1

    hits = search(
        index,
        args.query,
        embedder,
        mode=mode,
        top_k=top_k,
        candidate_k=candidate_k,
        rrf_k=rrf_k,
        team=args.team,
        acl=args.acl,
        priority=args.priority,
        source_id=args.source_id,
    )

    payload = {
        "query": args.query,
        "mode": mode,
        "filters": {
            "team": args.team,
            "acl": args.acl,
            "priority": args.priority,
            "source_id": args.source_id,
        },
        "embedding_model": index.meta.get("embedding_model"),
        "hits": [],
    }
    for h in hits:
        row = h.to_dict()
        text = row["text"]
        if args.text_chars > 0 and len(text) > args.text_chars:
            row["text"] = text[: args.text_chars].rstrip() + "…"
        payload["hits"].append(row)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
