"""Пункт 1: chunks.jsonl → embeddings.npz + embeddings_meta.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .embedders import Embedder


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            chunks.append(json.loads(line))
    return chunks


def load_previous(npz_path: Path, meta_path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any] | None]:
    """chunk_id → vector из предыдущего прогона (если модель совпадает)."""
    if not npz_path.exists() or not meta_path.exists():
        return {}, None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    data = np.load(npz_path, allow_pickle=False)
    ids = [str(x) for x in data["chunk_ids"].tolist()]
    vectors = data["vectors"]
    by_id = {cid: vectors[i] for i, cid in enumerate(ids)}
    return by_id, meta


def embed_chunks(
    chunks: list[dict[str, Any]],
    embedder: Embedder,
    *,
    previous: dict[str, np.ndarray] | None = None,
    previous_meta: dict[str, Any] | None = None,
    batch_size: int = 16,
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """
    Вернуть vectors (N, dim), chunk_ids, report.
    Переиспользует previous, если тот же model_name и content_hash совпал
    (hash храним в meta.chunk_hashes).
    """
    previous = previous or {}
    prev_hashes = {}
    if previous_meta and previous_meta.get("model_name") == embedder.model_name:
        prev_hashes = previous_meta.get("chunk_hashes") or {}

    ids: list[str] = []
    texts_to_embed: list[str] = []
    embed_positions: list[int] = []
    vectors: list[np.ndarray | None] = [None] * len(chunks)
    reused = 0

    for i, chunk in enumerate(chunks):
        cid = chunk["chunk_id"]
        ids.append(cid)
        chash = chunk.get("content_hash", "")
        if (
            cid in previous
            and prev_hashes.get(cid) == chash
            and previous[cid].shape[-1] == embedder.dim
        ):
            vectors[i] = previous[cid]
            reused += 1
        else:
            texts_to_embed.append(chunk["text"])
            embed_positions.append(i)

    if texts_to_embed:
        # batch
        for start in range(0, len(texts_to_embed), batch_size):
            batch_texts = texts_to_embed[start : start + batch_size]
            batch_pos = embed_positions[start : start + batch_size]
            batch_vecs = embedder.embed_passages(batch_texts)
            for local_i, pos in enumerate(batch_pos):
                vectors[pos] = batch_vecs[local_i]

    matrix = np.stack([v for v in vectors if v is not None], axis=0).astype(np.float32)
    chunk_hashes = {c["chunk_id"]: c.get("content_hash", "") for c in chunks}
    report = {
        "model_name": embedder.model_name,
        "dim": embedder.dim,
        "chunks_total": len(chunks),
        "embedded_new": len(texts_to_embed),
        "reused": reused,
        "backend": type(embedder).__name__,
    }
    meta = {
        "model_name": embedder.model_name,
        "dim": embedder.dim,
        "count": len(ids),
        "chunk_hashes": chunk_hashes,
        "normalize": True,
    }
    return matrix, ids, {"report": report, "meta": meta}


def write_embeddings(
    output_dir: Path,
    vectors: np.ndarray,
    chunk_ids: list[str],
    meta: dict[str, Any],
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    npz_path = output_dir / "embeddings.npz"
    meta_path = output_dir / "embeddings_meta.json"
    np.savez_compressed(
        npz_path,
        vectors=vectors,
        chunk_ids=np.array(chunk_ids, dtype=str),
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return npz_path, meta_path
