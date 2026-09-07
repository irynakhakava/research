"""Тесты пункта 1 (embeddings) — backend hash, без сети."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-2-retrieval"))

import numpy as np

from retrieval.config import load_config
from retrieval.embed_chunks import embed_chunks, load_chunks, write_embeddings
from retrieval.embedders import HashEmbedder, create_embedder


class TestEmbeddings(unittest.TestCase):
    def test_config_defaults(self) -> None:
        cfg = load_config()
        self.assertEqual(cfg["embeddings"]["model_name"], "intfloat/multilingual-e5-small")
        self.assertTrue(str(cfg["embeddings"]["passage_prefix"]).startswith("passage:"))

    def test_hash_embedder_shape_and_norm(self) -> None:
        emb = HashEmbedder(dim=64, normalize=True)
        vecs = emb.embed_passages(["hello", "world"])
        self.assertEqual(vecs.shape, (2, 64))
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, np.ones(2), atol=1e-5)

    def test_hash_deterministic(self) -> None:
        emb = HashEmbedder(dim=32)
        a = emb.embed_passages(["same text"])
        b = emb.embed_passages(["same text"])
        np.testing.assert_array_equal(a, b)

    def test_embed_chunks_from_processed(self) -> None:
        chunks_path = ROOT / "data" / "processed" / "chunks.jsonl"
        if not chunks_path.exists():
            self.skipTest("chunks.jsonl missing — run phase-1 pipeline first")
        chunks = load_chunks(chunks_path)
        self.assertGreaterEqual(len(chunks), 1)
        embedder = create_embedder({"backend": "hash", "normalize": True})
        vectors, ids, payload = embed_chunks(chunks, embedder, batch_size=8)
        self.assertEqual(len(ids), len(chunks))
        self.assertEqual(vectors.shape[0], len(chunks))
        self.assertEqual(payload["report"]["embedded_new"], len(chunks))

    def test_reuse_by_content_hash(self) -> None:
        chunks = [
            {
                "chunk_id": "a::0000",
                "text": "alpha",
                "content_hash": "sha256:aaa",
            },
            {
                "chunk_id": "b::0000",
                "text": "beta",
                "content_hash": "sha256:bbb",
            },
        ]
        emb = HashEmbedder(dim=16)
        v1, ids, payload = embed_chunks(chunks, emb)
        prev = {ids[i]: v1[i] for i in range(len(ids))}
        v2, _, payload2 = embed_chunks(
            chunks, emb, previous=prev, previous_meta=payload["meta"]
        )
        self.assertEqual(payload2["report"]["reused"], 2)
        self.assertEqual(payload2["report"]["embedded_new"], 0)
        np.testing.assert_array_equal(v1, v2)

    def test_write_npz(self) -> None:
        emb = HashEmbedder(dim=8)
        chunks = [{"chunk_id": "x::0000", "text": "t", "content_hash": "h"}]
        vectors, ids, payload = embed_chunks(chunks, emb)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            npz_path, meta_path = write_embeddings(out, vectors, ids, payload["meta"])
            self.assertTrue(npz_path.exists())
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["count"], 1)
            data = np.load(npz_path)
            self.assertEqual(data["vectors"].shape, (1, 8))


if __name__ == "__main__":
    unittest.main()
