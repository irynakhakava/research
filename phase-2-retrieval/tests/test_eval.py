"""Тесты пункта 5: Recall@k / MRR / select cases."""

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
from retrieval.eval import (
    evaluate_hits,
    first_relevant_rank,
    ranked_doc_ids,
    recall_at_k,
    reciprocal_rank,
    run_eval,
    select_eval_cases,
)
from retrieval.index import build_index, load_index
from retrieval.retrieve import SearchHit


class TestEvalMetrics(unittest.TestCase):
    def test_ranked_doc_ids_dedupes(self) -> None:
        hits = [
            SearchHit("a::0", 1.0, "a", "s", "t", "acl", [], "x"),
            SearchHit("a::1", 0.9, "a", "s", "t", "acl", [], "y"),
            SearchHit("b::0", 0.8, "b", "s", "t", "acl", [], "z"),
        ]
        self.assertEqual(ranked_doc_ids(hits), ["a", "b"])

    def test_recall_and_mrr(self) -> None:
        self.assertEqual(first_relevant_rank(["x", "y", "z"], ["y"]), 2)
        self.assertIsNone(first_relevant_rank(["x"], ["y"]))
        self.assertEqual(recall_at_k(2, 1), 0.0)
        self.assertEqual(recall_at_k(2, 5), 1.0)
        self.assertAlmostEqual(reciprocal_rank(2), 0.5)
        self.assertEqual(reciprocal_rank(None), 0.0)
        self.assertEqual(reciprocal_rank(5, k=3), 0.0)

    def test_select_skips_refuse_and_p1(self) -> None:
        items = [
            {
                "id": "q-1",
                "expected_behavior": "answer",
                "source_priority": "p0",
                "relevant_doc_ids": ["d1"],
                "primary_doc_id": "d1",
            },
            {
                "id": "q-2",
                "expected_behavior": "refuse",
                "source_priority": "p0",
                "relevant_doc_ids": [],
            },
            {
                "id": "q-3",
                "expected_behavior": "answer",
                "source_priority": "p1",
                "relevant_doc_ids": ["d2"],
                "primary_doc_id": "d2",
            },
        ]
        selected = select_eval_cases(items, priorities=["p0"])
        self.assertEqual([x["id"] for x in selected], ["q-1"])

    def test_evaluate_hits_aggregates(self) -> None:
        cases = [
            {
                "id": "q-a",
                "question": "a?",
                "relevant_doc_ids": ["doc-a"],
                "primary_doc_id": "doc-a",
            },
            {
                "id": "q-b",
                "question": "b?",
                "relevant_doc_ids": ["doc-b"],
                "primary_doc_id": "doc-b",
            },
        ]
        hits_by_id = {
            "q-a": [SearchHit("doc-a::0", 1.0, "doc-a", "s", "t", "acl", [], "t")],
            "q-b": [
                SearchHit("other::0", 1.0, "other", "s", "t", "acl", [], "t"),
                SearchHit("doc-b::0", 0.5, "doc-b", "s", "t", "acl", [], "t"),
            ],
        }
        report = evaluate_hits(cases, hits_by_id, k_values=(1, 10), mrr_k=10)
        self.assertEqual(report.n_cases, 2)
        self.assertAlmostEqual(report.metrics["recall_at_1"], 0.5)
        self.assertAlmostEqual(report.metrics["recall_at_10"], 1.0)
        # ranks 1 and 2 → MRR = (1 + 0.5) / 2
        self.assertAlmostEqual(report.metrics["mrr"], 0.75)
        self.assertTrue(report.passed["recall_at_10"])
        self.assertTrue(report.passed["mrr"])

    def test_run_eval_end_to_end_hash(self) -> None:
        chunks = [
            {
                "chunk_id": "plat-runbook-payments-rollback::0000",
                "doc_id": "plat-runbook-payments-rollback",
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
                "chunk_id": "other::0000",
                "doc_id": "other-doc",
                "source_id": "x",
                "text": "unrelated celery queue metrics",
                "content_hash": "h2",
                "acl": "public-to-company",
                "team": "data",
                "priority": "p0",
                "language": "en",
                "heading_path": ["Misc"],
                "char_count": 30,
            },
        ]
        gold = [
            {
                "id": "q-001-payments-rollback",
                "question": "rollback payments staging",
                "query_type": "how-to",
                "expected_behavior": "answer",
                "relevant_doc_ids": ["plat-runbook-payments-rollback"],
                "primary_doc_id": "plat-runbook-payments-rollback",
                "source_priority": "p0",
            }
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
            report = run_eval(
                index,
                emb,
                gold,
                mode="hybrid",
                top_k=5,
                k_values=(1, 5, 10),
                priorities=["p0"],
            )
            self.assertEqual(report.n_cases, 1)
            self.assertEqual(report.metrics["recall_at_10"], 1.0)
            self.assertGreater(report.metrics["mrr"], 0.0)


if __name__ == "__main__":
    unittest.main()
