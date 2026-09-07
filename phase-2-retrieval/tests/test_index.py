"""Тесты пункта 2: BM25 + сборка индекса."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-2-retrieval"))

import numpy as np

from retrieval.bm25 import build_bm25, tokenize
from retrieval.embed_chunks import embed_chunks, write_embeddings
from retrieval.embedders import HashEmbedder
from retrieval.index import build_index, load_index


class TestIndex(unittest.TestCase):
    def test_tokenize_ru_en(self) -> None:
        tokens = tokenize("Rollback payments в staging")
        self.assertIn("rollback", tokens)
        self.assertIn("staging", tokens)
        self.assertIn("payments", tokens)

    def test_bm25_ranks_relevant(self) -> None:
        ids = ["a", "b", "c"]
        texts = [
            "как откатить релиз payments staging rollback",
            "airflow backfill dag",
            "oncall rotation pagerduty",
        ]
        idx = build_bm25(ids, texts)
        hits = idx.score("rollback payments staging", top_k=2)
        self.assertEqual(hits[0][0], "a")
        self.assertGreater(hits[0][1], 0)

    def test_build_and_load_index(self) -> None:
        chunks_path = ROOT / "data" / "processed" / "chunks.jsonl"
        if not chunks_path.exists():
            self.skipTest("chunks.jsonl missing")

        # tiny synthetic embeddings aligned to real chunks
        import json

        chunks = [
            json.loads(l)
            for l in chunks_path.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ][:5]
        emb = HashEmbedder(dim=16)
        vectors, ids, payload = embed_chunks(chunks, emb)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # write mini chunks file
            mini_chunks = tmp_path / "chunks.jsonl"
            mini_chunks.write_text(
                "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n",
                encoding="utf-8",
            )
            npz, meta = write_embeddings(tmp_path, vectors, ids, payload["meta"])
            index_dir = tmp_path / "index"
            report = build_index(
                chunks_path=mini_chunks,
                embeddings_npz=npz,
                embeddings_meta_path=meta,
                index_dir=index_dir,
            )
            self.assertEqual(report["n_chunks"], 5)
            loaded = load_index(index_dir)
            self.assertEqual(len(loaded.chunk_ids), 5)
            bm25_hits = loaded.score_bm25(chunks[0]["text"][:80], top_k=3)
            self.assertTrue(bm25_hits)
            # dense: query = first vector
            dense_hits = loaded.score_dense(loaded.vectors[0], top_k=3)
            self.assertEqual(dense_hits[0][0], loaded.chunk_ids[0])

    def test_full_processed_index_smoke(self) -> None:
        emb = ROOT / "data" / "processed" / "embeddings.npz"
        meta = ROOT / "data" / "processed" / "embeddings_meta.json"
        chunks = ROOT / "data" / "processed" / "chunks.jsonl"
        if not emb.exists():
            self.skipTest("embeddings.npz missing")
        with tempfile.TemporaryDirectory() as tmp:
            report = build_index(
                chunks_path=chunks,
                embeddings_npz=emb,
                embeddings_meta_path=meta,
                index_dir=Path(tmp) / "index",
            )
            self.assertEqual(report["n_chunks"], 40)


if __name__ == "__main__":
    unittest.main()
