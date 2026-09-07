"""Пункт 3: hybrid retrieve + metadata filters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from .embedders import Embedder
from .index import HybridIndex


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    doc_id: str
    source_id: str
    team: str
    acl: str
    heading_path: list[str]
    text: str
    dense_rank: int | None = None
    bm25_rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "score": self.score,
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "team": self.team,
            "acl": self.acl,
            "heading_path": self.heading_path,
            "text": self.text,
            "dense_rank": self.dense_rank,
            "bm25_rank": self.bm25_rank,
        }


def rrf_fuse(
    rankings: Sequence[Sequence[tuple[str, float]]],
    *,
    k: int = 60,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion по нескольким спискам (id, score)."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, (cid, _) in enumerate(ranking, start=1):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]


def filter_chunk_ids(
    index: HybridIndex,
    *,
    team: str | None = None,
    acl: str | None = None,
    priority: str | None = None,
    source_id: str | None = None,
) -> set[str] | None:
    """None = без фильтра; иначе allowlist chunk_id."""
    if not any([team, acl, priority, source_id]):
        return None
    allowed: set[str] = set()
    for cid, meta in index.chunks_by_id.items():
        if team and meta.get("team") != team:
            continue
        if acl and meta.get("acl") != acl:
            continue
        if priority and meta.get("priority") != priority:
            continue
        if source_id and meta.get("source_id") != source_id:
            continue
        allowed.add(cid)
    return allowed


def _filter_ranking(
    ranking: list[tuple[str, float]],
    allowed: set[str] | None,
) -> list[tuple[str, float]]:
    if allowed is None:
        return ranking
    return [(cid, s) for cid, s in ranking if cid in allowed]


def search(
    index: HybridIndex,
    query: str,
    embedder: Embedder,
    *,
    mode: str = "hybrid",
    top_k: int = 5,
    candidate_k: int = 20,
    rrf_k: int = 60,
    team: str | None = None,
    acl: str | None = None,
    priority: str | None = None,
    source_id: str | None = None,
) -> list[SearchHit]:
    """
    mode: dense | bm25 | hybrid
    Фильтры применяются до выдачи (ACL-safe: чужие чанки не попадают в ranking).
    """
    allowed = filter_chunk_ids(
        index, team=team, acl=acl, priority=priority, source_id=source_id
    )
    if allowed is not None and len(allowed) == 0:
        return []

    dense_ranking: list[tuple[str, float]] = []
    bm25_ranking: list[tuple[str, float]] = []

    if mode in {"dense", "hybrid"}:
        q_vec = embedder.embed_queries([query])[0]
        # score all then filter — ok for N≈40; for large N mask indices
        dense_ranking = _filter_ranking(
            index.score_dense(q_vec, top_k=max(candidate_k, top_k) * 3),
            allowed,
        )[:candidate_k]

    if mode in {"bm25", "hybrid"}:
        bm25_ranking = _filter_ranking(
            index.score_bm25(query, top_k=max(candidate_k, top_k) * 3),
            allowed,
        )[:candidate_k]

    if mode == "dense":
        fused = dense_ranking[:top_k]
    elif mode == "bm25":
        fused = bm25_ranking[:top_k]
    elif mode == "hybrid":
        fused = rrf_fuse([dense_ranking, bm25_ranking], k=rrf_k, top_k=top_k)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    dense_rank = {cid: i + 1 for i, (cid, _) in enumerate(dense_ranking)}
    bm25_rank = {cid: i + 1 for i, (cid, _) in enumerate(bm25_ranking)}

    hits: list[SearchHit] = []
    for cid, score in fused:
        meta = index.chunks_by_id.get(cid, {})
        hits.append(
            SearchHit(
                chunk_id=cid,
                score=float(score),
                doc_id=str(meta.get("doc_id", "")),
                source_id=str(meta.get("source_id", "")),
                team=str(meta.get("team", "")),
                acl=str(meta.get("acl", "")),
                heading_path=list(meta.get("heading_path") or []),
                text=str(meta.get("text", "")),
                dense_rank=dense_rank.get(cid),
                bm25_rank=bm25_rank.get(cid),
            )
        )
    return hits
