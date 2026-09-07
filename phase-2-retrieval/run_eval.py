#!/usr/bin/env python3
"""Фаза 2 · пункт 5: offline eval Recall@k / MRR на gold-set.

Примеры:
  python phase-2-retrieval/run_eval.py
  python phase-2-retrieval/run_eval.py --mode hybrid --compare dense,bm25
  python phase-2-retrieval/run_eval.py --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval.config import REPO_ROOT, load_config
from retrieval.embedders import create_embedder
from retrieval.eval import load_gold_set, run_eval, select_eval_cases, write_report
from retrieval.index import load_index


def _parse_ks(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _parse_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2.5: offline retrieval eval")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default=None)
    parser.add_argument(
        "--compare",
        default=None,
        help="Доп. режимы через запятую, например dense,bm25",
    )
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--ks", default=None, help="Список k, напр. 1,5,10")
    parser.add_argument("--priorities", default=None, help="p0 или p0,p1")
    parser.add_argument("--gold-set", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None, help="Первые N answer-кейсов")
    parser.add_argument(
        "--backend",
        choices=["sentence_transformers", "hash"],
        default=None,
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--fail-under-threshold",
        action="store_true",
        help="Exit 1 если Recall@10 или MRR ниже порогов DoD",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    eval_cfg = dict(cfg.get("eval") or {})
    retrieve_cfg = dict(cfg.get("retrieve") or {})

    mode = args.mode or str(eval_cfg.get("mode") or retrieve_cfg.get("mode", "hybrid"))
    top_k = args.top_k if args.top_k is not None else int(eval_cfg.get("top_k", 10))
    ks = (
        _parse_ks(args.ks)
        if args.ks
        else [int(x) for x in (eval_cfg.get("k_values") or [1, 5, 10])]
    )
    priorities = (
        _parse_csv(args.priorities)
        if args.priorities
        else [str(x) for x in (eval_cfg.get("priorities") or ["p0"])]
    )
    rrf_k = int(retrieve_cfg.get("rrf_k", 60))
    candidate_k = int(eval_cfg.get("candidate_k") or retrieve_cfg.get("candidate_k", 40))
    thresholds = {
        "recall_at_10": float(eval_cfg.get("threshold_recall_at_10", 0.70)),
        "mrr": float(eval_cfg.get("threshold_mrr", 0.50)),
    }

    gold_path = args.gold_set or cfg["gold_set_path"]
    if not gold_path.exists():
        print(f"ERROR: gold-set not found: {gold_path}", file=sys.stderr)
        return 1

    index_dir = cfg["index_dir"]
    if not (index_dir / "index_meta.json").exists():
        print(f"ERROR: index not found at {index_dir}", file=sys.stderr)
        print("Run: python phase-2-retrieval/run_index.py", file=sys.stderr)
        return 1

    index = load_index(index_dir)
    emb_cfg = dict(cfg["embeddings"])
    if args.backend:
        emb_cfg["backend"] = args.backend

    if emb_cfg["backend"] == "hash" and index.vectors.shape[1] != 64:
        print(
            f"ERROR: hash embedder dim=64 but index dim={index.vectors.shape[1]}. "
            "Use sentence_transformers for e5 index.",
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

    gold_items = load_gold_set(gold_path)
    selected = select_eval_cases(gold_items, priorities=priorities)
    if args.limit is not None:
        selected = selected[: args.limit]

    modes = [mode]
    if args.compare:
        for m in _parse_csv(args.compare):
            if m not in modes:
                modes.append(m)

    reports = []
    for m in modes:
        if m not in {"hybrid", "dense", "bm25"}:
            print(f"ERROR: unknown mode {m}", file=sys.stderr)
            return 1
        if m in {"dense", "hybrid"} and embedder.dim != index.vectors.shape[1]:
            print(f"SKIP mode={m}: dim mismatch", file=sys.stderr)
            continue
        reports.append(
            run_eval(
                index,
                embedder,
                selected,
                mode=m,
                top_k=top_k,
                candidate_k=candidate_k,
                rrf_k=rrf_k,
                k_values=ks,
                mrr_k=max(ks) if ks else 10,
                priorities=priorities,
                thresholds=thresholds,
            )
        )

    if not reports:
        print("ERROR: no eval reports produced", file=sys.stderr)
        return 1

    out_path = args.output
    if out_path is None:
        out_path = Path(str(eval_cfg.get("output_path") or "data/processed/eval_report.json"))
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path

    write_report(reports[0], out_path)

    summary: dict = {
        "gold_set": str(gold_path),
        "index_dir": str(index_dir),
        "report_path": str(out_path),
        "priorities": priorities,
        "modes": [],
    }
    all_ok = True
    hit_key = 10 if 10 in (reports[0].k_values) else max(reports[0].k_values)
    for report in reports:
        summary["modes"].append(
            {
                "mode": report.mode,
                "n_cases": report.n_cases,
                "metrics": report.metrics,
                "thresholds": report.thresholds,
                "passed": report.passed,
                "misses": [
                    {
                        "id": c.id,
                        "question": c.question,
                        "relevant_doc_ids": c.relevant_doc_ids,
                        "retrieved_doc_ids": c.retrieved_doc_ids[:5],
                    }
                    for c in report.cases
                    if not c.hit_at.get(hit_key, False)
                ],
            }
        )
        if not all(report.passed.values()):
            all_ok = False

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.fail_under_threshold and not all_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
