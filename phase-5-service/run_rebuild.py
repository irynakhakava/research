#!/usr/bin/env python3
"""Одна команда: corpus → chunks → embeddings → index.

  python phase-5-service/run_rebuild.py
  python phase-5-service/run_rebuild.py --dry-run
  python phase-5-service/run_rebuild.py --backend hash
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run(argv: list[str], *, dry_run: bool) -> int:
    print("+ " + " ".join(argv), file=sys.stderr)
    if dry_run:
        return 0
    proc = subprocess.run(argv, cwd=REPO)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5: rebuild index from corpus")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--backend",
        choices=["sentence_transformers", "hash"],
        default="sentence_transformers",
        help="Embed backend (hash — для CI/тестов)",
    )
    parser.add_argument("--no-reuse", action="store_true")
    args = parser.parse_args()
    py = sys.executable
    steps = [
        [py, str(REPO / "phase-1-data" / "run_pipeline.py")],
        [
            py,
            str(REPO / "phase-2-retrieval" / "run_embed.py"),
            "--backend",
            args.backend,
            *(["--no-reuse"] if args.no_reuse else []),
        ],
        [py, str(REPO / "phase-2-retrieval" / "run_index.py")],
    ]
    if args.dry_run:
        for step in steps:
            print("+ " + " ".join(step) + "  # dry-run")
        print("dry-run: skip execute")
        return 0

    for step in steps:
        code = _run(step, dry_run=False)
        if code != 0:
            print(f"ERROR: step failed ({code}): {' '.join(step)}", file=sys.stderr)
            return code
    print("rebuild ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
