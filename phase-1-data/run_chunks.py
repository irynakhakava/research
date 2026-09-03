#!/usr/bin/env python3
"""CLI шага 3: documents → chunks.jsonl (structure-aware B).

Примеры:
  python phase-1-data/run_chunks.py
  python phase-1-data/run_chunks.py --from-documents data/processed/documents.jsonl
  python phase-1-data/run_chunks.py --max-chars 1200 --overlap 150
  python phase-1-data/run_chunks.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.chunking import chunk_documents
from pipeline.config import REPO_ROOT, load_config
from pipeline.load import (
    load_normalized_documents,
    write_documents_jsonl,
    write_report,
)


def _load_documents_jsonl(path: Path) -> list[dict]:
    docs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            docs.append(json.loads(line))
    return docs


def _write_chunks_jsonl(chunks: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(c, ensure_ascii=False) for c in chunks]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 step 3: build chunks.jsonl")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--priority",
        default=None,
        help="Comma-separated priorities when rebuilding docs (default: config)",
    )
    parser.add_argument(
        "--from-documents",
        type=Path,
        default=None,
        help="Read documents.jsonl instead of reloading corpus",
    )
    parser.add_argument("--max-chars", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    parser.add_argument("--min-chars", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--write-documents",
        action="store_true",
        help="Also refresh documents.jsonl when loading from corpus",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    chunking = dict(cfg["chunking"])
    if args.max_chars is not None:
        chunking["max_chars"] = args.max_chars
    if args.overlap is not None:
        chunking["overlap"] = args.overlap
    if args.min_chars is not None:
        chunking["min_chars"] = args.min_chars

    if args.from_documents:
        docs_path = args.from_documents
        if not docs_path.is_absolute():
            docs_path = REPO_ROOT / docs_path
        documents = _load_documents_jsonl(docs_path)
        doc_report = {"source": str(docs_path), "docs_out": len(documents)}
    else:
        priorities = (
            [p.strip() for p in args.priority.split(",") if p.strip()]
            if args.priority
            else list(cfg["priorities"])
        )
        documents, doc_report = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=priorities,
            exclude_priorities=cfg["exclude_priorities"],
        )
        if doc_report.get("errors"):
            for err in doc_report["errors"]:
                print(f"ERROR: {err}", file=sys.stderr)
            return 1
        if args.write_documents and not args.dry_run:
            write_documents_jsonl(documents, cfg["output_dir"] / "documents.jsonl")

    chunks, chunk_report = chunk_documents(
        documents,
        max_chars=int(chunking["max_chars"]),
        overlap=int(chunking["overlap"]),
        min_chars=int(chunking["min_chars"]),
    )
    report = {
        "documents": doc_report,
        "chunking": chunk_report,
        "dry_run": args.dry_run,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if chunk_report.get("empty_docs"):
        print(f"WARN: empty docs: {chunk_report['empty_docs']}", file=sys.stderr)

    if args.dry_run:
        print(f"dry-run: would write {len(chunks)} chunks")
        return 0

    out_dir: Path = cfg["output_dir"]
    chunks_path = out_dir / "chunks.jsonl"
    report_path = out_dir / "pipeline_report.json"
    _write_chunks_jsonl(chunks, chunks_path)
    write_report(report, report_path)
    print(f"wrote {chunks_path} ({len(chunks)} chunks)")
    print(f"wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
