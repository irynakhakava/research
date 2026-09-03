#!/usr/bin/env python3
"""CLI шагов 1–2 фазы 1: scope p0 + documents.jsonl.

Примеры:
  python phase-1-data/run_documents.py
  python phase-1-data/run_documents.py --priority p0,p1
  python phase-1-data/run_documents.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# позволяет запускать файл напрямую
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.config import REPO_ROOT, load_config
from pipeline.load import load_normalized_documents, write_documents_jsonl, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 steps 1–2: build documents.jsonl")
    parser.add_argument(
        "--priority",
        default=None,
        help="Comma-separated priorities (default from config.yaml, usually p0)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Не писать файлы, только печатать report",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    priorities = (
        [p.strip() for p in args.priority.split(",") if p.strip()]
        if args.priority
        else list(cfg["priorities"])
    )

    documents, report = load_normalized_documents(
        repo_root=REPO_ROOT,
        corpus_root=cfg["corpus_root"],
        catalog_path=cfg["catalog_path"],
        priorities=priorities,
        exclude_priorities=cfg["exclude_priorities"],
    )
    report["dry_run"] = args.dry_run

    print(json.dumps({k: report[k] for k in report if k != "errors"}, ensure_ascii=False, indent=2))
    if report["errors"]:
        print("ERRORS:", file=sys.stderr)
        for err in report["errors"]:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"dry-run: would write {len(documents)} documents")
        return 0

    out_dir: Path = cfg["output_dir"]
    docs_path = out_dir / "documents.jsonl"
    report_path = out_dir / "documents_build_report.json"
    write_documents_jsonl(documents, docs_path)
    write_report(report, report_path)
    print(f"wrote {docs_path} ({len(documents)} docs)")
    print(f"wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
