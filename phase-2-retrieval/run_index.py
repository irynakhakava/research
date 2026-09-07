#!/usr/bin/env python3
"""Фаза 2 · пункт 2: собрать dense + BM25 индекс.

Примеры:
  python phase-2-retrieval/run_index.py
  python phase-2-retrieval/run_index.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval.config import REPO_ROOT, load_config
from retrieval.index import build_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2.2: build dense+BM25 index")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = cfg["output_dir"]
    chunks_path = cfg["chunks_path"]
    emb_npz = out_dir / "embeddings.npz"
    emb_meta = out_dir / "embeddings_meta.json"
    index_dir = Path(cfg.get("index_dir", out_dir / "index"))
    if not index_dir.is_absolute():
        index_dir = REPO_ROOT / index_dir

    index_cfg = cfg.get("index") or {}
    k1 = float(index_cfg.get("bm25_k1", 1.5))
    b = float(index_cfg.get("bm25_b", 0.75))

    for path, label in [
        (chunks_path, "chunks.jsonl"),
        (emb_npz, "embeddings.npz"),
        (emb_meta, "embeddings_meta.json"),
    ]:
        if not path.exists():
            print(f"ERROR: missing {label}: {path}", file=sys.stderr)
            if "embed" in label or path.name.startswith("embeddings"):
                print("Run: python phase-2-retrieval/run_embed.py --backend hash", file=sys.stderr)
            else:
                print("Run: python phase-1-data/run_pipeline.py", file=sys.stderr)
            return 1

    preview = {
        "chunks_path": str(chunks_path),
        "embeddings_npz": str(emb_npz),
        "index_dir": str(index_dir),
        "bm25_k1": k1,
        "bm25_b": b,
        "dry_run": args.dry_run,
    }
    print(json.dumps(preview, ensure_ascii=False, indent=2))

    if args.dry_run:
        print("dry-run: skip write")
        return 0

    report = build_index(
        chunks_path=chunks_path,
        embeddings_npz=emb_npz,
        embeddings_meta_path=emb_meta,
        index_dir=index_dir,
        bm25_k1=k1,
        bm25_b=b,
    )
    report_path = index_dir / "build_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote index → {index_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
