"""Сборка citations[]: path + url из documents.jsonl и каталога источников."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

_PHASE2 = Path(__file__).resolve().parents[2] / "phase-2-retrieval"
if str(_PHASE2) not in sys.path:
    sys.path.insert(0, str(_PHASE2))

from retrieval.retrieve import SearchHit


@dataclass
class Citation:
    index: int
    chunk_id: str
    doc_id: str
    source_id: str
    path: str
    url: str
    heading_path: list[str]
    quote: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "path": self.path,
            "url": self.url,
            "heading_path": self.heading_path,
            "quote": self.quote,
        }


def load_document_paths(documents_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not documents_path.exists():
        return mapping
    for line in documents_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        doc_id = str(row.get("doc_id") or "")
        path = str(row.get("path") or "")
        if doc_id:
            mapping[doc_id] = path
    return mapping


def load_source_locations(catalog_path: Path) -> dict[str, str]:
    """source_id → location URL из sources.catalog.yaml (без PyYAML)."""
    locations: dict[str, str] = {}
    if not catalog_path.exists():
        return locations
    current_id: str | None = None
    for raw in catalog_path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("- id:"):
            current_id = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            continue
        if current_id and stripped.startswith("location:"):
            loc = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            locations[current_id] = loc
    return locations


def _quote(text: str, max_chars: int) -> str:
    compact = " ".join((text or "").split())
    if max_chars > 0 and len(compact) > max_chars:
        return compact[:max_chars].rstrip() + "…"
    return compact


def citation_url(source_id: str, doc_id: str, locations: dict[str, str]) -> str:
    base = locations.get(source_id, "").rstrip("/")
    if not base:
        return f"nordledger://docs/{doc_id}"
    return f"{base}#{doc_id}"


def build_citations(
    hits: Sequence[SearchHit],
    *,
    documents_by_id: dict[str, str],
    locations: dict[str, str],
    quote_chars: int = 280,
    limit: int | None = None,
) -> list[Citation]:
    seen_chunks: set[str] = set()
    citations: list[Citation] = []
    rows = list(hits) if limit is None else list(hits)[:limit]
    for hit in rows:
        if hit.chunk_id in seen_chunks:
            continue
        seen_chunks.add(hit.chunk_id)
        path = documents_by_id.get(hit.doc_id, "")
        if not path:
            path = f"data/corpus/{hit.source_id}/{hit.doc_id}.md"
        citations.append(
            Citation(
                index=len(citations) + 1,
                chunk_id=hit.chunk_id,
                doc_id=hit.doc_id,
                source_id=hit.source_id,
                path=path,
                url=citation_url(hit.source_id, hit.doc_id, locations),
                heading_path=list(hit.heading_path or []),
                quote=_quote(hit.text, quote_chars),
            )
        )
    return citations
