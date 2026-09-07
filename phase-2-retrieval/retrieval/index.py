"""Пункт 2: сборка dense + BM25 индекса на диске."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .bm25 import BM25Index, build_bm25


@dataclass
class HybridIndex:
    """Загруженный индекс для scoring (retrieve — пункт 3)."""

    chunk_ids: list[str]
    vectors: np.ndarray  # (N, dim), L2-normalized preferred
    bm25: BM25Index
    chunks_by_id: dict[str, dict[str, Any]]
    meta: dict[str, Any]

    def score_dense(self, query_vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        q = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        if q.shape[0] != self.vectors.shape[1]:
            raise ValueError(
                f"dim mismatch: query {q.shape[0]} vs index {self.vectors.shape[1]}"
            )
        # assume normalized → cosine = dot
        scores = self.vectors @ q
        order = np.argsort(-scores)[:top_k]
        return [(self.chunk_ids[i], float(scores[i])) for i in order]

    def score_bm25(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        return self.bm25.score(query, top_k=top_k)


def _load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunks.append(json.loads(line))
    return chunks


def build_index(
    *,
    chunks_path: Path,
    embeddings_npz: Path,
    embeddings_meta_path: Path,
    index_dir: Path,
    bm25_k1: float = 1.5,
    bm25_b: float = 0.75,
) -> dict[str, Any]:
    chunks = _load_chunks(chunks_path)
    chunks_by_id = {c["chunk_id"]: c for c in chunks}

    emb_meta = json.loads(embeddings_meta_path.read_text(encoding="utf-8"))
    data = np.load(embeddings_npz, allow_pickle=False)
    emb_ids = [str(x) for x in data["chunk_ids"].tolist()]
    vectors = np.asarray(data["vectors"], dtype=np.float32)

    if len(emb_ids) != vectors.shape[0]:
        raise ValueError("embeddings chunk_ids / vectors length mismatch")

    missing = [cid for cid in emb_ids if cid not in chunks_by_id]
    if missing:
        raise ValueError(f"embeddings refer to unknown chunks: {missing[:5]}")

    # keep embedding order as canonical index order
    ordered_chunks = [chunks_by_id[cid] for cid in emb_ids]
    texts = [c["text"] for c in ordered_chunks]
    bm25 = build_bm25(emb_ids, texts, k1=bm25_k1, b=bm25_b)

    index_dir.mkdir(parents=True, exist_ok=True)
    dense_path = index_dir / "dense.npz"
    bm25_path = index_dir / "bm25.json"
    meta_path = index_dir / "index_meta.json"
    chunks_meta_path = index_dir / "chunks_meta.jsonl"

    np.savez_compressed(dense_path, vectors=vectors, chunk_ids=np.array(emb_ids, dtype=str))
    bm25_path.write_text(
        json.dumps(bm25.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8"
    )

    with chunks_meta_path.open("w", encoding="utf-8") as fh:
        for c in ordered_chunks:
            row = {
                "chunk_id": c["chunk_id"],
                "doc_id": c["doc_id"],
                "source_id": c["source_id"],
                "acl": c.get("acl"),
                "team": c.get("team"),
                "priority": c.get("priority"),
                "language": c.get("language"),
                "heading_path": c.get("heading_path"),
                "content_hash": c.get("content_hash"),
                "char_count": c.get("char_count"),
                "text": c["text"],
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "n_chunks": len(emb_ids),
        "dim": int(vectors.shape[1]),
        "embedding_model": emb_meta.get("model_name"),
        "chunks_path": str(chunks_path),
        "embeddings_npz": str(embeddings_npz),
        "bm25": {"k1": bm25_k1, "b": bm25_b, "vocab_size": len(bm25.df)},
        "files": {
            "dense": "dense.npz",
            "bm25": "bm25.json",
            "chunks_meta": "chunks_meta.jsonl",
        },
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "index_dir": str(index_dir),
        "n_chunks": len(emb_ids),
        "dim": int(vectors.shape[1]),
        "embedding_model": emb_meta.get("model_name"),
        "bm25_vocab_size": len(bm25.df),
        "files": meta["files"],
    }


def load_index(index_dir: Path) -> HybridIndex:
    meta = json.loads((index_dir / "index_meta.json").read_text(encoding="utf-8"))
    dense = np.load(index_dir / "dense.npz", allow_pickle=False)
    chunk_ids = [str(x) for x in dense["chunk_ids"].tolist()]
    vectors = np.asarray(dense["vectors"], dtype=np.float32)
    bm25 = BM25Index.from_dict(
        json.loads((index_dir / "bm25.json").read_text(encoding="utf-8"))
    )
    chunks_by_id: dict[str, dict[str, Any]] = {}
    for line in (index_dir / "chunks_meta.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            chunks_by_id[row["chunk_id"]] = row
    return HybridIndex(
        chunk_ids=chunk_ids,
        vectors=vectors,
        bm25=bm25,
        chunks_by_id=chunks_by_id,
        meta=meta,
    )
