"""Пункт 1 фазы 3: вопрос → retrieve → refuse или grounded answer + citations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from retrieval.embedders import Embedder
from retrieval.index import HybridIndex
from retrieval.retrieve import SearchHit, search

from .citations import Citation, build_citations
from .generators import generate_extractive, generate_openai, resolve_api_key
from .refuse import classify_query_refuse, refuse_message


@dataclass
class AskResponse:
    question: str
    answer: str
    refuse: bool
    refuse_reason: str | None
    citations: list[Citation]
    retrieved_chunk_ids: list[str]
    mode: str
    generation_backend: str
    generation_model: str
    confidence: float | None = None
    filters: dict[str, str | None] = field(default_factory=dict)
    embedding_model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "refuse": self.refuse,
            "refuse_reason": self.refuse_reason,
            "citations": [c.to_dict() for c in self.citations],
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "mode": self.mode,
            "generation_backend": self.generation_backend,
            "generation_model": self.generation_model,
            "confidence": self.confidence,
            "filters": self.filters,
            "embedding_model": self.embedding_model,
        }


def max_dense_score(
    index: HybridIndex,
    embedder: Embedder,
    query: str,
    hits: list[SearchHit],
) -> float | None:
    if not hits:
        return 0.0
    try:
        q_vec = embedder.embed_queries([query])[0]
    except Exception:
        return None
    q = np.asarray(q_vec, dtype=np.float32).reshape(-1)
    if q.shape[0] != index.vectors.shape[1]:
        return None
    id_to_i = {cid: i for i, cid in enumerate(index.chunk_ids)}
    scores: list[float] = []
    for hit in hits:
        i = id_to_i.get(hit.chunk_id)
        if i is None:
            continue
        scores.append(float(index.vectors[i] @ q))
    return max(scores) if scores else 0.0


def _nearest_unique_hits(hits: list[SearchHit], limit: int) -> list[SearchHit]:
    seen: set[str] = set()
    out: list[SearchHit] = []
    for hit in hits:
        if hit.doc_id in seen:
            continue
        seen.add(hit.doc_id)
        out.append(hit)
        if len(out) >= limit:
            break
    return out


def ask(
    index: HybridIndex,
    embedder: Embedder,
    question: str,
    *,
    documents_by_id: dict[str, str],
    locations: dict[str, str],
    mode: str = "hybrid",
    top_k: int = 5,
    candidate_k: int = 20,
    rrf_k: int = 60,
    team: str | None = None,
    acl: str | None = None,
    priority: str | None = None,
    source_id: str | None = None,
    generation_backend: str = "extractive",
    generation_model: str = "extractive",
    max_context_chunks: int = 4,
    min_dense_score: float = 0.28,
    nearest_links: int = 3,
    quote_chars: int = 280,
    openai_base_url: str = "https://api.openai.com/v1",
    skip_query_refuse: bool = False,
) -> AskResponse:
    """
    Контракт будущего HTTP POST /ask.
    Политика низкой уверенности: refuse_with_nearest_links (NFR).
    """
    filters = {
        "team": team,
        "acl": acl,
        "priority": priority,
        "source_id": source_id,
    }
    hits = search(
        index,
        question,
        embedder,
        mode=mode,
        top_k=max(top_k, nearest_links),
        candidate_k=candidate_k,
        rrf_k=rrf_k,
        team=team,
        acl=acl,
        priority=priority,
        source_id=source_id,
    )
    retrieved_ids = [h.chunk_id for h in hits]
    confidence = max_dense_score(index, embedder, question, hits)

    reason = None if skip_query_refuse else classify_query_refuse(question)
    if reason is None and not hits:
        reason = "empty_retrieval"
    if (
        reason is None
        and confidence is not None
        and float(min_dense_score) > 0
        and confidence < float(min_dense_score)
    ):
        reason = "low_confidence"

    if reason:
        nearest = _nearest_unique_hits(hits, nearest_links)
        citations = build_citations(
            nearest,
            documents_by_id=documents_by_id,
            locations=locations,
            quote_chars=quote_chars,
        )
        extra = ""
        if citations:
            extra = "\n\nБлижайшие документы (без утверждения фактов):\n" + "\n".join(
                f"- [{c.index}] {c.path or c.doc_id}" for c in citations
            )
        return AskResponse(
            question=question,
            answer=refuse_message(reason) + extra,
            refuse=True,
            refuse_reason=reason,
            citations=citations,
            retrieved_chunk_ids=retrieved_ids,
            mode=mode,
            generation_backend=generation_backend,
            generation_model=generation_model,
            confidence=confidence,
            filters=filters,
            embedding_model=index.meta.get("embedding_model"),
        )

    context_hits = hits[:max_context_chunks]
    citations = build_citations(
        context_hits,
        documents_by_id=documents_by_id,
        locations=locations,
        quote_chars=quote_chars,
    )

    backend = generation_backend
    model_name = generation_model
    if backend == "extractive":
        answer = generate_extractive(
            question, context_hits, citations, max_chunks=max_context_chunks
        )
    elif backend in {"openai", "llm"}:
        api_key = resolve_api_key()
        if not api_key:
            raise RuntimeError(
                "generation backend=openai requires OPENAI_API_KEY or LLM_API_KEY"
            )
        answer = generate_openai(
            question,
            context_hits,
            citations,
            model=model_name,
            base_url=openai_base_url,
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unknown generation backend: {backend}")

    return AskResponse(
        question=question,
        answer=answer,
        refuse=False,
        refuse_reason=None,
        citations=citations,
        retrieved_chunk_ids=retrieved_ids,
        mode=mode,
        generation_backend=backend,
        generation_model=model_name,
        confidence=confidence,
        filters=filters,
        embedding_model=index.meta.get("embedding_model"),
    )
