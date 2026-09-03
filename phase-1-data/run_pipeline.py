#!/usr/bin/env python3
"""Шаг 4: единый CLI фазы 1 — corpus → documents.jsonl + chunks.jsonl + report.

Примеры:
  python phase-1-data/run_pipeline.py
  python phase-1-data/run_pipeline.py --priority p0,p1
  python phase-1-data/run_pipeline.py --dry-run
  python phase-1-data/run_pipeline.py --max-chars 1200 --overlap 150
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.chunking import chunk_documents
from pipeline.config import REPO_ROOT, load_config
from pipeline.load import load_normalized_documents, write_documents_jsonl, write_report
from pipeline.quality import run_quality_checks


def _write_chunks_jsonl(chunks: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(c, ensure_ascii=False) for c in chunks]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 1 unified pipeline: documents + chunks + quality"
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--priority",
        default=None,
        help="Comma-separated priorities (default from config.yaml)",
    )
    parser.add_argument("--max-chars", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    parser.add_argument("--min-chars", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-quality-fail",
        action="store_true",
        help="Write outputs even if quality checks fail (exit code still 1)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    priorities = (
        [p.strip() for p in args.priority.split(",") if p.strip()]
        if args.priority
        else list(cfg["priorities"])
    )
    chunking = dict(cfg["chunking"])
    if args.max_chars is not None:
        chunking["max_chars"] = args.max_chars
    if args.overlap is not None:
        chunking["overlap"] = args.overlap
    if args.min_chars is not None:
        chunking["min_chars"] = args.min_chars

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

    chunks, chunk_report = chunk_documents(
        documents,
        max_chars=int(chunking["max_chars"]),
        overlap=int(chunking["overlap"]),
        min_chars=int(chunking["min_chars"]),
    )

    quality = run_quality_checks(
        documents=documents,
        chunks=chunks,
        gold_path=cfg["gold_set_path"],
        priorities=priorities,
    )

    report = {
        "step": "run_pipeline",
        "config": {
            "priorities": priorities,
            "max_chars": chunking["max_chars"],
            "overlap": chunking["overlap"],
            "min_chars": chunking["min_chars"],
            "strategy": chunking.get("strategy", "structure_b"),
        },
        "documents": {
            "docs_out": doc_report.get("docs_out"),
            "skipped_outside_priority": doc_report.get("skipped_outside_priority"),
            "by_source_id": doc_report.get("by_source_id"),
            "scoped_source_ids": doc_report.get("scoped_source_ids"),
        },
        "chunking": chunk_report,
        "quality": quality,
        "dry_run": args.dry_run,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not quality["ok"]:
        print("QUALITY FAIL", file=sys.stderr)
        if quality["orphans"].get("orphan_doc_ids"):
            print(f"  orphans: {quality['orphans']['orphan_doc_ids']}", file=sys.stderr)
        if quality["goldset_p0"].get("missing_doc_ids"):
            print(
                f"  gold missing: {quality['goldset_p0']['missing_doc_ids']}",
                file=sys.stderr,
            )
        if quality["chunk_metadata"].get("errors"):
            print(
                f"  metadata: {quality['chunk_metadata']['errors']}",
                file=sys.stderr,
            )

    if args.dry_run:
        print(
            f"dry-run: would write {len(documents)} documents, {len(chunks)} chunks"
        )
        return 0 if quality["ok"] else 1

    if quality["ok"] or args.skip_quality_fail:
        out_dir: Path = cfg["output_dir"]
        docs_path = out_dir / "documents.jsonl"
        chunks_path = out_dir / "chunks.jsonl"
        report_path = out_dir / "pipeline_report.json"
        write_documents_jsonl(documents, docs_path)
        _write_chunks_jsonl(chunks, chunks_path)
        write_report(report, report_path)
        print(f"wrote {docs_path} ({len(documents)} docs)")
        print(f"wrote {chunks_path} ({len(chunks)} chunks)")
        print(f"wrote {report_path}")
    else:
        print(
            "outputs not written due to quality fail (use --skip-quality-fail)",
            file=sys.stderr,
        )

    return 0 if quality["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
