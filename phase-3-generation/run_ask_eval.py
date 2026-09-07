#!/usr/bin/env python3
"""Фаза 3: eval /ask на gold-set (refuse + citations contract).

  python phase-3-generation/run_ask_eval.py
  python phase-3-generation/run_ask_eval.py --answer-limit 5 --fail-under-threshold
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase-2-retrieval"))

from generation.citations import load_document_paths, load_source_locations
from generation.config import REPO_ROOT, load_config
from generation.eval import load_gold_set, run_ask_eval
from retrieval.embedders import create_embedder
from retrieval.index import load_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: /ask eval")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--answer-limit", type=int, default=None)
    parser.add_argument("--backend", choices=["extractive", "openai"], default=None)
    parser.add_argument(
        "--embed-backend",
        choices=["sentence_transformers", "hash"],
        default=None,
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--fail-under-threshold", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    retrieve_cfg = dict(cfg.get("retrieve") or {})
    gen_cfg = dict(cfg.get("generation") or {})
    eval_cfg = dict(cfg.get("eval") or {})

    index = load_index(cfg["index_dir"])
    emb_cfg = dict(cfg["embeddings"])
    if args.embed_backend:
        emb_cfg["backend"] = args.embed_backend
    try:
        embedder = create_embedder(emb_cfg)
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    gold = load_gold_set(cfg["gold_set_path"])
    gen_backend = args.backend or str(gen_cfg.get("backend", "extractive"))
    ask_kwargs = {
        "documents_by_id": load_document_paths(cfg["documents_path"]),
        "locations": load_source_locations(cfg["catalog_path"]),
        "mode": str(retrieve_cfg.get("mode", "hybrid")),
        "top_k": int(retrieve_cfg.get("top_k", 5)),
        "candidate_k": int(retrieve_cfg.get("candidate_k", 20)),
        "rrf_k": int(retrieve_cfg.get("rrf_k", 60)),
        "generation_backend": gen_backend,
        "generation_model": str(gen_cfg.get("model_name", gen_backend)),
        "max_context_chunks": int(gen_cfg.get("max_context_chunks", 4)),
        "min_dense_score": float(gen_cfg.get("min_dense_score", 0.28)),
        "nearest_links": int(gen_cfg.get("nearest_links", 3)),
        "quote_chars": int(gen_cfg.get("quote_chars", 280)),
        "openai_base_url": str(gen_cfg.get("openai_base_url", "https://api.openai.com/v1")),
    }
    report = run_ask_eval(
        index,
        embedder,
        gold,
        ask_kwargs=ask_kwargs,
        answer_limit=args.answer_limit
        if args.answer_limit is not None
        else (int(eval_cfg["answer_limit"]) if eval_cfg.get("answer_limit") else None),
        threshold_refuse=float(eval_cfg.get("threshold_refuse_rate", 0.90)),
        threshold_citations=float(eval_cfg.get("threshold_citation_rate", 1.0)),
        threshold_grounded=float(eval_cfg.get("threshold_grounded_rate", 0.80)),
    )
    out = args.output
    if out is None:
        out = Path(str(eval_cfg.get("output_path") or "data/processed/ask_eval_report.json"))
        if not out.is_absolute():
            out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
    summary = {
        "report_path": str(out),
        "n_refuse_cases": report.n_refuse_cases,
        "n_answer_cases": report.n_answer_cases,
        "refuse_rate": report.refuse_rate,
        "citation_contract_rate": report.citation_contract_rate,
        "grounded_rate": report.grounded_rate,
        "passed": report.passed,
        "refuse_fails": [
            c for c in report.cases if c["expected_behavior"] == "refuse" and not c["refuse"]
        ],
        "ungrounded": [
            c
            for c in report.cases
            if c["expected_behavior"] == "answer" and not c["grounded_ok"]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.fail_under_threshold and not all(report.passed.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
