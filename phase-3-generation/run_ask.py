#!/usr/bin/env python3
"""Фаза 3: вопрос → ответ + citations[] (контракт /ask).

Примеры:
  python phase-3-generation/run_ask.py "Как откатить payments в staging?"
  python phase-3-generation/run_ask.py "Какой пароль от прод-БД payments?"
  python phase-3-generation/run_ask.py "rollback" --team platform
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-2-retrieval"))

from generation.ask import ask
from generation.citations import load_document_paths, load_source_locations
from generation.config import load_config
from retrieval.embedders import create_embedder
from retrieval.index import load_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: RAG /ask")
    parser.add_argument("question", help="Вопрос на естественном языке")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--acl", default=None)
    parser.add_argument("--priority", default=None)
    parser.add_argument("--source-id", default=None)
    parser.add_argument(
        "--backend",
        choices=["extractive", "openai"],
        default=None,
        help="Генератор ответа (extractive — без LLM API)",
    )
    parser.add_argument(
        "--embed-backend",
        choices=["sentence_transformers", "hash"],
        default=None,
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    retrieve_cfg = dict(cfg.get("retrieve") or {})
    gen_cfg = dict(cfg.get("generation") or {})

    mode = args.mode or str(retrieve_cfg.get("mode", "hybrid"))
    top_k = args.top_k if args.top_k is not None else int(retrieve_cfg.get("top_k", 5))
    gen_backend = args.backend or str(gen_cfg.get("backend", "extractive"))

    index_dir = cfg["index_dir"]
    if not (index_dir / "index_meta.json").exists():
        print(f"ERROR: index not found at {index_dir}", file=sys.stderr)
        print("Run: python phase-2-retrieval/run_index.py", file=sys.stderr)
        return 1

    index = load_index(index_dir)
    emb_cfg = dict(cfg["embeddings"])
    if args.embed_backend:
        emb_cfg["backend"] = args.embed_backend
    if emb_cfg["backend"] == "hash" and index.vectors.shape[1] != 64:
        print(
            f"ERROR: hash embedder dim=64 but index dim={index.vectors.shape[1]}",
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

    resp = ask(
        index,
        embedder,
        args.question,
        documents_by_id=load_document_paths(cfg["documents_path"]),
        locations=load_source_locations(cfg["catalog_path"]),
        mode=mode,
        top_k=top_k,
        candidate_k=int(retrieve_cfg.get("candidate_k", 20)),
        rrf_k=int(retrieve_cfg.get("rrf_k", 60)),
        team=args.team,
        acl=args.acl,
        priority=args.priority,
        source_id=args.source_id,
        generation_backend=gen_backend,
        generation_model=str(
            gen_cfg.get("openai_model")
            if gen_backend == "openai"
            else gen_cfg.get("model_name", gen_backend)
        ),
        max_context_chunks=int(gen_cfg.get("max_context_chunks", 4)),
        min_dense_score=float(gen_cfg.get("min_dense_score", 0.28)),
        nearest_links=int(gen_cfg.get("nearest_links", 3)),
        quote_chars=int(gen_cfg.get("quote_chars", 280)),
        openai_base_url=str(gen_cfg.get("openai_base_url", "https://api.openai.com/v1")),
    )
    print(json.dumps(resp.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
