#!/usr/bin/env python3
"""Фаза 2 · пункт 1: построить embeddings для chunks.jsonl.

Примеры:
  python phase-2-retrieval/run_embed.py
  python phase-2-retrieval/run_embed.py --backend hash
  python phase-2-retrieval/run_embed.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval.config import load_config
from retrieval.embed_chunks import embed_chunks, load_chunks, load_previous, write_embeddings
from retrieval.embedders import create_embedder


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2.1: embed chunks")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--backend",
        choices=["sentence_transformers", "hash"],
        default=None,
        help="Override embeddings.backend from config",
    )
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--chunks", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-reuse",
        action="store_true",
        help="Ignore previous embeddings.npz and recompute all",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    emb_cfg = dict(cfg["embeddings"])
    if args.backend:
        emb_cfg["backend"] = args.backend
    if args.model_name:
        emb_cfg["model_name"] = args.model_name

    chunks_path = args.chunks or cfg["chunks_path"]
    if not chunks_path.is_absolute():
        from retrieval.config import REPO_ROOT

        chunks_path = REPO_ROOT / chunks_path

    if not chunks_path.exists():
        print(f"ERROR: chunks not found: {chunks_path}", file=sys.stderr)
        print("Run: python phase-1-data/run_pipeline.py", file=sys.stderr)
        return 1

    chunks = load_chunks(chunks_path)
    print(
        json.dumps(
            {
                "chunks_path": str(chunks_path),
                "chunks": len(chunks),
                "backend": emb_cfg["backend"],
                "model_name": emb_cfg.get("model_name"),
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.dry_run:
        print("dry-run: skip model load / write")
        return 0

    try:
        embedder = create_embedder(emb_cfg)
    except ImportError as exc:
        print(
            "ERROR: sentence-transformers not installed. "
            "pip install -r phase-2-retrieval/requirements.txt\n"
            f"Detail: {exc}",
            file=sys.stderr,
        )
        return 1

    out_dir = cfg["output_dir"]
    previous: dict = {}
    previous_meta = None
    if not args.no_reuse:
        previous, previous_meta = load_previous(
            out_dir / "embeddings.npz", out_dir / "embeddings_meta.json"
        )

    vectors, chunk_ids, payload = embed_chunks(
        chunks,
        embedder,
        previous=previous,
        previous_meta=previous_meta,
        batch_size=int(emb_cfg.get("batch_size", 16)),
    )
    npz_path, meta_path = write_embeddings(out_dir, vectors, chunk_ids, payload["meta"])

    print(json.dumps(payload["report"], ensure_ascii=False, indent=2))
    print(f"wrote {npz_path} shape={vectors.shape}")
    print(f"wrote {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
