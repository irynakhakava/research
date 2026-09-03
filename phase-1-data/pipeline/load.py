"""Шаги 1–2: scope по priority + загрузка/нормализация документов."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import SourceMeta, filter_sources_by_priority, load_catalog
from .normalize import build_document


def load_manifest(corpus_root: Path) -> list[dict[str, str]]:
    manifest_path = corpus_root / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return list(data["documents"])


def resolve_repo_path(repo_root: Path, rel: str) -> Path:
    return repo_root / rel


def load_normalized_documents(
    *,
    repo_root: Path,
    corpus_root: Path,
    catalog_path: Path,
    priorities: list[str],
    exclude_priorities: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    1) Читает catalog, оставляет source_id с нужным priority (шаг 1).
    2) Берёт файлы из manifest, join по source_id, нормализует (шаг 2).
    """
    catalog = load_catalog(catalog_path)
    scoped = filter_sources_by_priority(catalog, priorities, exclude_priorities)
    scoped_ids = set(scoped)

    manifest_docs = load_manifest(corpus_root)
    documents: list[dict[str, Any]] = []
    skipped_priority = 0
    errors: list[str] = []

    for entry in manifest_docs:
        source_id = entry["source_id"]
        if source_id not in scoped_ids:
            skipped_priority += 1
            continue

        meta: SourceMeta = scoped[source_id]
        rel_path = entry["path"]
        abs_path = resolve_repo_path(repo_root, rel_path)
        if not abs_path.exists():
            errors.append(f"missing file: {rel_path}")
            continue

        raw = abs_path.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(abs_path.stat().st_mtime, tz=timezone.utc).date().isoformat()

        try:
            doc = build_document(
                path_rel=rel_path,
                raw_markdown=raw,
                source_id=source_id,
                acl=meta.acl,
                team=meta.team,
                priority=meta.priority,
                doc_types=meta.doc_types,
                default_language=(meta.languages[0] if meta.languages else "ru"),
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if not doc.get("updated_at"):
            doc["updated_at"] = mtime
        documents.append(doc)

    documents.sort(key=lambda d: d["doc_id"])

    report = {
        "priorities": priorities,
        "scoped_source_ids": sorted(scoped_ids),
        "manifest_docs_total": len(manifest_docs),
        "docs_out": len(documents),
        "skipped_outside_priority": skipped_priority,
        "errors": errors,
        "by_source_id": _count_by_source(documents),
    }
    return documents, report


def _count_by_source(documents: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for doc in documents:
        sid = doc["source_id"]
        counts[sid] = counts.get(sid, 0) + 1
    return dict(sorted(counts.items()))


def write_documents_jsonl(documents: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(doc, ensure_ascii=False) for doc in documents]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
