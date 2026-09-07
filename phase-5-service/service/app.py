"""Обработчики POST /search, POST /ask, GET /health."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from generation.ask import ask
from generation.citations import load_document_paths, load_source_locations
from retrieval.embedders import Embedder, create_embedder
from retrieval.index import HybridIndex, load_index
from retrieval.retrieve import search

from .loggingutil import log_event


@dataclass
class AppContext:
    index: HybridIndex
    embedder: Embedder
    retrieve: dict[str, Any]
    generation: dict[str, Any]
    documents_by_id: dict[str, str]
    locations: dict[str, str]


def load_context(cfg: dict[str, Any], *, embed_backend: str | None = None) -> AppContext:
    index = load_index(cfg["index_dir"])
    emb_cfg = dict(cfg["embeddings"])
    if embed_backend:
        emb_cfg["backend"] = embed_backend
    embedder = create_embedder(emb_cfg)
    if embedder.dim != index.vectors.shape[1]:
        raise RuntimeError(
            f"embedder dim={embedder.dim} != index dim={index.vectors.shape[1]}"
        )
    return AppContext(
        index=index,
        embedder=embedder,
        retrieve=dict(cfg.get("retrieve") or {}),
        generation=dict(cfg.get("generation") or {}),
        documents_by_id=load_document_paths(cfg["documents_path"]),
        locations=load_source_locations(cfg["catalog_path"]),
    )


def _filters(body: dict[str, Any]) -> dict[str, str | None]:
    return {
        "team": body.get("team"),
        "acl": body.get("acl"),
        "priority": body.get("priority"),
        "source_id": body.get("source_id"),
    }


def _clip_text(text: str, limit: int) -> str:
    if limit > 0 and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def do_search(
    ctx: AppContext,
    body: dict[str, Any],
    *,
    trace_id: str,
    text_chars: int = 280,
) -> tuple[int, dict[str, Any]]:
    question = str(body.get("question") or body.get("query") or "").strip()
    if not question:
        return 400, {"error": "question is required", "trace_id": trace_id}
    retrieve = ctx.retrieve
    mode = str(body.get("mode") or retrieve.get("mode", "hybrid"))
    if mode not in {"hybrid", "dense", "bm25"}:
        return 400, {"error": f"unknown mode: {mode}", "trace_id": trace_id}
    top_k = int(body.get("top_k") or retrieve.get("top_k", 5))
    filters = _filters(body)
    t0 = time.perf_counter()
    hits = search(
        ctx.index,
        question,
        ctx.embedder,
        mode=mode,
        top_k=top_k,
        candidate_k=int(retrieve.get("candidate_k", 20)),
        rrf_k=int(retrieve.get("rrf_k", 60)),
        team=filters["team"],
        acl=filters["acl"],
        priority=filters["priority"],
        source_id=filters["source_id"],
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    rows = []
    for hit in hits:
        row = hit.to_dict()
        row["text"] = _clip_text(str(row.get("text") or ""), text_chars)
        rows.append(row)
    payload = {
        "trace_id": trace_id,
        "query": question,
        "mode": mode,
        "filters": filters,
        "embedding_model": ctx.index.meta.get("embedding_model"),
        "hits": rows,
    }
    log_event(
        {
            "trace_id": trace_id,
            "event": "search",
            "mode": mode,
            "filters": filters,
            "retrieved_chunk_ids": [h.chunk_id for h in hits],
            "embedding_model": ctx.index.meta.get("embedding_model"),
            "llm_model": None,
            "refuse": False,
            "latency_ms": latency_ms,
            "hit_count": len(hits),
        }
    )
    return 200, payload


def do_ask(
    ctx: AppContext,
    body: dict[str, Any],
    *,
    trace_id: str,
) -> tuple[int, dict[str, Any]]:
    question = str(body.get("question") or body.get("query") or "").strip()
    if not question:
        return 400, {"error": "question is required", "trace_id": trace_id}
    retrieve = ctx.retrieve
    gen = ctx.generation
    mode = str(body.get("mode") or retrieve.get("mode", "hybrid"))
    filters = _filters(body)
    t0 = time.perf_counter()
    resp = ask(
        ctx.index,
        ctx.embedder,
        question,
        documents_by_id=ctx.documents_by_id,
        locations=ctx.locations,
        mode=mode,
        top_k=int(body.get("top_k") or retrieve.get("top_k", 5)),
        candidate_k=int(retrieve.get("candidate_k", 20)),
        rrf_k=int(retrieve.get("rrf_k", 60)),
        team=filters["team"],
        acl=filters["acl"],
        priority=filters["priority"],
        source_id=filters["source_id"],
        generation_backend=str(gen.get("backend", "extractive")),
        generation_model=str(gen.get("model_name", "extractive")),
        max_context_chunks=int(gen.get("max_context_chunks", 4)),
        min_dense_score=float(gen.get("min_dense_score", 0.28)),
        nearest_links=int(gen.get("nearest_links", 3)),
        quote_chars=int(gen.get("quote_chars", 280)),
        openai_base_url=str(gen.get("openai_base_url", "https://api.openai.com/v1")),
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    payload = resp.to_dict()
    payload["trace_id"] = trace_id
    log_event(
        {
            "trace_id": trace_id,
            "event": "ask",
            "mode": mode,
            "filters": filters,
            "retrieved_chunk_ids": resp.retrieved_chunk_ids,
            "embedding_model": resp.embedding_model,
            "llm_model": resp.generation_model,
            "refuse": resp.refuse,
            "refuse_reason": resp.refuse_reason,
            "latency_ms": latency_ms,
            "citation_count": len(resp.citations),
        }
    )
    return 200, payload


def health_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "nordledger-doc-search",
        "endpoints": ["GET /health", "POST /search", "POST /ask"],
    }
