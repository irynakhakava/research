"""Тесты пункта 3: RRF, filters, search smoke."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-2-retrieval"))

from retrieval.embed_chunks import embed_chunks, write_embeddings
from retrieval.embedders import HashEmbedder
from retrieval.index import build_index, load_index
from retrieval.retrieve import filter_chunk_ids, rrf_fuse, search


class TestRetrieve(unittest.TestCase):
    def test_rrf_prefers_consensus(self) -> None:
        dense = [("a", 0.9), ("b", 0.8), ("c", 0.1)]
        bm25 = [("b", 5.0), ("a", 4.0), ("d", 1.0)]
        fused = rrf_fuse([dense, bm25], k=60, top_k=3)
        # a and b appear in both → should lead
        top_ids = [cid for cid, _ in fused]
        self.assertIn("a", top_ids[:2])
        self.assertIn("b", top_ids[:2])

    def test_filter_and_hybrid_search(self) -> None:
        chunks = [
            {
                "chunk_id": "plat::0000",
                "doc_id": "plat",
                "source_id": "platform-confluence-runbooks",
                "text": "Как откатить релиз payments staging rollback pipeline",
                "content_hash": "h1",
                "acl": "team-only",
                "team": "platform",
                "priority": "p0",
                "language": "ru",
                "heading_path": ["Rollback"],
                "char_count": 50,
            },
            {
                "chunk_id": "data::0000",
                "doc_id": "data",
                "source_id": "data-git-airflow-runbooks",
                "text": "Airflow backfill dag retry stuck task",
                "content_hash": "h2",
                "acl": "public-to-company",
                "team": "data",
                "priority": "p0",
                "language": "en",
                "heading_path": ["Backfill"],
                "char_count": 40,
            },
        ]
        emb = HashEmbedder(dim=32)
        vectors, ids, payload = embed_chunks(chunks, emb)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chunks_path = tmp_path / "chunks.jsonl"
            chunks_path.write_text(
                "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n",
                encoding="utf-8",
            )
            npz, meta = write_embeddings(tmp_path, vectors, ids, payload["meta"])
            index_dir = tmp_path / "index"
            build_index(
                chunks_path=chunks_path,
                embeddings_npz=npz,
                embeddings_meta_path=meta,
                index_dir=index_dir,
            )
            index = load_index(index_dir)

            allowed = filter_chunk_ids(index, team="platform")
            self.assertEqual(allowed, {"plat::0000"})

            hits = search(
                index,
                "rollback payments staging",
                emb,
                mode="hybrid",
                top_k=2,
            )
            self.assertGreaterEqual(len(hits), 1)
            self.assertEqual(hits[0].chunk_id, "plat::0000")

            filtered = search(
                index,
                "rollback payments staging",
                emb,
                mode="hybrid",
                top_k=5,
                team="data",
            )
            # platform chunk must not leak
            self.assertTrue(all(h.team == "data" for h in filtered))
            self.assertTrue(all(h.chunk_id != "plat::0000" for h in filtered))

    def test_bm25_only_no_embedder_dim_issue(self) -> None:
        # bm25 mode still needs embedder object but won't call embed_queries
        chunks = [
            {
                "chunk_id": "x::0000",
                "doc_id": "x",
                "source_id": "s",
                "text": "kubectl crashloop payments diagnose",
                "content_hash": "hx",
                "acl": "team-only",
                "team": "platform",
                "priority": "p0",
                "language": "ru",
                "heading_path": ["Debug"],
                "char_count": 30,
            }
        ]
        emb = HashEmbedder(dim=16)
        vectors, ids, payload = embed_chunks(chunks, emb)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chunks_path = tmp_path / "chunks.jsonl"
            chunks_path.write_text(json.dumps(chunks[0], ensure_ascii=False) + "\n")
            npz, meta = write_embeddings(tmp_path, vectors, ids, payload["meta"])
            index_dir = tmp_path / "index"
            build_index(
                chunks_path=chunks_path,
                embeddings_npz=npz,
                embeddings_meta_path=meta,
                index_dir=index_dir,
            )
            index = load_index(index_dir)
            hits = search(index, "kubectl crashloop", emb, mode="bm25", top_k=1)
            self.assertEqual(hits[0].chunk_id, "x::0000")


if __name__ == "__main__":
    unittest.main()
