#!/usr/bin/env python3
"""Проверяет, что все sample_doc_ids и relevant_doc_ids из gold-set есть в корпусе."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
CATALOG = REPO / "phase-0-discovery" / "sources.catalog.yaml"
GOLD = REPO / "phase-0-discovery" / "gold-set" / "dataset.jsonl"
MANIFEST = ROOT / "manifest.json"


def catalog_sample_ids() -> set[str]:
    ids: set[str] = set()
    in_samples = False
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("sample_doc_ids:"):
            in_samples = True
            continue
        if in_samples:
            m = re.match(r"\s+-\s+([a-z0-9-]+)\s*$", line)
            if m:
                ids.add(m.group(1))
                continue
            if line.strip() and not line.strip().startswith("#") and not line.startswith(" "):
                in_samples = False
            elif line.strip() and not line.strip().startswith("-") and not line.strip().startswith("#"):
                # следующий ключ того же уровня внутри source (notes:)
                if re.match(r"\s{4}[a-z_]+:", line):
                    in_samples = False
    return ids


def gold_doc_ids() -> set[str]:
    ids: set[str] = set()
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        for doc_id in item.get("relevant_doc_ids") or []:
            ids.add(doc_id)
        primary = item.get("primary_doc_id")
        if primary:
            ids.add(primary)
    return ids


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {d["id"]: d for d in manifest["documents"]}
    on_disk = {p.stem for p in ROOT.glob("*/*.md")}

    required = catalog_sample_ids() | gold_doc_ids()
    missing_manifest = sorted(required - set(by_id))
    missing_disk = sorted(required - on_disk)

    print(f"Документов в manifest: {len(by_id)}")
    print(f"Требуется (catalog samples ∪ gold-set): {len(required)}")

    errors = 0
    if missing_manifest:
        errors += 1
        print("FAIL: нет в manifest.json:", missing_manifest)
    if missing_disk:
        errors += 1
        print("FAIL: нет .md на диске:", missing_disk)

    for doc_id, meta in by_id.items():
        path = REPO / meta["path"]
        if not path.exists():
            errors += 1
            print(f"FAIL: path из manifest не существует: {meta['path']}")

    if errors:
        return 1
    print("OK: корпус покрывает catalog sample_doc_ids и gold-set relevant_doc_ids")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
