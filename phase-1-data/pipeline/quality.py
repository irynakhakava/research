"""Шаг 5: проверки качества после documents/chunks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_gold_set(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def p0_relevant_doc_ids(gold_items: list[dict[str, Any]]) -> set[str]:
    """doc_id, которые должны быть в documents при priority=p0."""
    ids: set[str] = set()
    for item in gold_items:
        if item.get("source_priority") != "p0":
            continue
        if item.get("expected_behavior") == "refuse":
            continue
        for doc_id in item.get("relevant_doc_ids") or []:
            ids.add(doc_id)
        primary = item.get("primary_doc_id")
        if primary:
            ids.add(primary)
    return ids


def check_orphans(
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Каждый document должен дать ≥1 chunk."""
    doc_ids = {d["doc_id"] for d in documents}
    chunk_docs = {c["doc_id"] for c in chunks}
    missing = sorted(doc_ids - chunk_docs)
    return {
        "ok": len(missing) == 0,
        "docs_in": len(doc_ids),
        "docs_with_chunks": len(chunk_docs & doc_ids),
        "orphan_doc_ids": missing,
    }


def check_goldset_coverage(
    documents: list[dict[str, Any]],
    gold_path: Path,
    *,
    priorities: list[str],
) -> dict[str, Any]:
    """Все p0 relevant_doc_ids из gold-set есть в documents (если p0 в scope)."""
    if "p0" not in priorities:
        return {
            "ok": True,
            "skipped": True,
            "reason": "p0 not in priorities — gold p0 smoke skipped",
        }

    gold_items = load_gold_set(gold_path)
    required = p0_relevant_doc_ids(gold_items)
    present = {d["doc_id"] for d in documents}
    missing = sorted(required - present)
    return {
        "ok": len(missing) == 0,
        "skipped": False,
        "required_count": len(required),
        "missing_doc_ids": missing,
        "gold_path": str(gold_path),
    }


def required_chunk_metadata_ok(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    required = [
        "chunk_id",
        "doc_id",
        "source_id",
        "chunk_index",
        "text",
        "heading_path",
        "acl",
        "team",
        "priority",
        "language",
        "content_hash",
    ]
    bad: list[str] = []
    for chunk in chunks:
        for key in required:
            if key not in chunk:
                bad.append(f"{chunk.get('chunk_id', '?')}: missing {key}")
                break
            if key == "heading_path" and not isinstance(chunk[key], list):
                bad.append(f"{chunk.get('chunk_id', '?')}: heading_path not list")
                break
    return {"ok": len(bad) == 0, "errors": bad[:20], "checked": len(chunks)}


def run_quality_checks(
    *,
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    gold_path: Path,
    priorities: list[str],
) -> dict[str, Any]:
    orphans = check_orphans(documents, chunks)
    gold = check_goldset_coverage(documents, gold_path, priorities=priorities)
    meta = required_chunk_metadata_ok(chunks)
    ok = orphans["ok"] and gold["ok"] and meta["ok"]
    return {
        "ok": ok,
        "orphans": orphans,
        "goldset_p0": gold,
        "chunk_metadata": meta,
    }
