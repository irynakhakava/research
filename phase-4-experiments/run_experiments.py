#!/usr/bin/env python3
"""Фаза 4: сравнения на gold-set (без нового сервиса).

  python phase-4-experiments/run_experiments.py
  python phase-4-experiments/run_experiments.py --only retrieval
  python phase-4-experiments/run_experiments.py --only ask --answer-limit 8
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-3-generation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-2-retrieval"))

from experiments.compare import pick_winners, run_ask_sweep, run_retrieval_sweep
from experiments.config import load_config
from experiments.report import to_markdown
from generation.citations import load_document_paths, load_source_locations
from generation.eval import load_gold_set
from generation.generators import resolve_api_key
from retrieval.embedders import create_embedder
from retrieval.index import load_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4: gold-set experiments")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--only", choices=["retrieval", "ask", "all"], default="all")
    parser.add_argument("--answer-limit", type=int, default=None)
    parser.add_argument(
        "--embed-backend",
        choices=["sentence_transformers", "hash"],
        default=None,
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    retrieve_cfg = dict(cfg.get("retrieve") or {})
    gen_cfg = dict(cfg.get("generation") or {})
    exp = dict(cfg.get("experiments") or {})

    index_dir = cfg["index_dir"]
    if not (index_dir / "index_meta.json").exists():
        print(f"ERROR: index not found at {index_dir}", file=sys.stderr)
        print("Run: python phase-2-retrieval/run_index.py", file=sys.stderr)
        return 1

    index = load_index(index_dir)
    emb_cfg = {
        "backend": "sentence_transformers",
        "model_name": "intfloat/multilingual-e5-small",
        "normalize": True,
        "passage_prefix": "passage: ",
        "query_prefix": "query: ",
        **dict(cfg.get("embeddings") or {}),
    }
    if args.embed_backend:
        emb_cfg["backend"] = args.embed_backend
    if emb_cfg["backend"] == "hash" and index.vectors.shape[1] != 64:
        print(
            f"ERROR: hash dim=64 but index dim={index.vectors.shape[1]}",
            file=sys.stderr,
        )
        return 1
    try:
        embedder = create_embedder(emb_cfg)
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    gold = load_gold_set(cfg["gold_set_path"])
    runs: list[dict] = []

    if args.only in {"all", "retrieval"}:
        runs.extend(
            run_retrieval_sweep(
                index,
                embedder,
                gold,
                modes=exp.get("retrieval_modes") or ["hybrid", "dense", "bm25"],
                top_k=int(retrieve_cfg.get("top_k", 10)),
                candidate_k=int(retrieve_cfg.get("candidate_k", 40)),
                rrf_k=int(retrieve_cfg.get("rrf_k", 60)),
            )
        )

    if args.only in {"all", "ask"}:
        backends = ["extractive"]
        if exp.get("include_openai") and resolve_api_key():
            backends.append("openai")
        elif exp.get("include_openai"):
            print("WARN: include_openai=true but no OPENAI_API_KEY — skip", file=sys.stderr)

        base_kwargs = {
            "documents_by_id": load_document_paths(cfg["documents_path"]),
            "locations": load_source_locations(cfg["catalog_path"]),
            "mode": str(retrieve_cfg.get("mode", "hybrid")),
            "candidate_k": int(retrieve_cfg.get("candidate_k", 20)),
            "rrf_k": int(retrieve_cfg.get("rrf_k", 60)),
            "generation_backend": str(gen_cfg.get("backend", "extractive")),
            "generation_model": str(gen_cfg.get("openai_model", "gpt-4o-mini")),
            "max_context_chunks": int(gen_cfg.get("max_context_chunks", 4)),
            "nearest_links": int(gen_cfg.get("nearest_links", 3)),
            "quote_chars": int(gen_cfg.get("quote_chars", 280)),
            "openai_base_url": str(gen_cfg.get("openai_base_url", "https://api.openai.com/v1")),
        }
        runs.extend(
            run_ask_sweep(
                index,
                embedder,
                gold,
                base_ask_kwargs=base_kwargs,
                min_dense_scores=exp.get("ask_min_dense_scores"),
                top_ks=exp.get("ask_top_ks"),
                answer_limit=args.answer_limit,
                generation_backends=backends,
            )
        )

    report = {
        "index_dir": str(index_dir),
        "gold_set": str(cfg["gold_set_path"]),
        "embedding_model": index.meta.get("embedding_model"),
        "only": args.only,
        "runs": runs,
        "winners": pick_winners(runs),
    }

    out_dir = args.output_dir or cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    md = to_markdown(report)
    md_path.write_text(md + "\n")
    print(md)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
