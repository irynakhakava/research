"""Тесты фазы 4: агрегаты и выбор победителя (без e5)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-4-experiments"))
sys.path.insert(0, str(ROOT / "phase-3-generation"))
sys.path.insert(0, str(ROOT / "phase-2-retrieval"))

from experiments.compare import pick_winners, run_retrieval_sweep, summarize_ask_cases
from experiments.report import to_markdown
from retrieval.embed_chunks import embed_chunks, write_embeddings
from retrieval.embedders import HashEmbedder
from retrieval.index import build_index, load_index


class TestExperimentHelpers(unittest.TestCase):
    def test_summarize_distinguishes_false_refuse(self) -> None:
        cases = [
            {"expected_behavior": "refuse", "refuse": True, "grounded_ok": True},
            {"expected_behavior": "answer", "refuse": True, "grounded_ok": True},
            {"expected_behavior": "answer", "refuse": False, "grounded_ok": True},
        ]
        extra = summarize_ask_cases(cases)
        self.assertEqual(extra["refuse_rate"], 1.0)
        self.assertEqual(extra["answered_rate"], 0.5)
        self.assertEqual(extra["grounded_among_answered"], 1.0)

    def test_pick_winners_prefers_higher_mrr(self) -> None:
        rows = [
            {
                "name": "retrieve:bm25",
                "kind": "retrieval",
                "params": {"mode": "bm25"},
                "metrics": {"recall_at_10": 1.0, "mrr": 0.80},
            },
            {
                "name": "retrieve:dense",
                "kind": "retrieval",
                "params": {"mode": "dense"},
                "metrics": {"recall_at_10": 1.0, "mrr": 0.97},
            },
        ]
        winners = pick_winners(rows)
        self.assertEqual(winners["retrieval"]["params"]["mode"], "dense")

    def test_markdown_contains_tables(self) -> None:
        md = to_markdown(
            {
                "index_dir": "/tmp/index",
                "gold_set": "/tmp/gold.jsonl",
                "runs": [
                    {
                        "kind": "retrieval",
                        "params": {"mode": "hybrid"},
                        "metrics": {
                            "recall_at_1": 0.8,
                            "recall_at_5": 1.0,
                            "recall_at_10": 1.0,
                            "mrr": 0.9,
                        },
                        "n_cases": 10,
                    }
                ],
                "winners": {
                    "retrieval": {
                        "params": {"mode": "hybrid"},
                        "recall_at_10": 1.0,
                        "mrr": 0.9,
                    }
                },
            }
        )
        self.assertIn("Recall@10", md)
        self.assertIn("hybrid", md)

    def test_retrieval_sweep_hash_index(self) -> None:
        chunks = [
            {
                "chunk_id": "plat::0000",
                "doc_id": "plat-runbook-payments-rollback",
                "source_id": "s",
                "text": "rollback payments staging pipeline",
                "content_hash": "h1",
                "acl": "team-only",
                "team": "platform",
                "priority": "p0",
                "language": "ru",
                "heading_path": ["Rollback"],
                "char_count": 30,
            }
        ]
        gold = [
            {
                "id": "q-001",
                "question": "rollback payments staging",
                "expected_behavior": "answer",
                "relevant_doc_ids": ["plat-runbook-payments-rollback"],
                "primary_doc_id": "plat-runbook-payments-rollback",
                "source_priority": "p0",
            }
        ]
        emb = HashEmbedder(dim=32)
        vectors, ids, payload = embed_chunks(chunks, emb)
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            chunks_path = tmp / "chunks.jsonl"
            chunks_path.write_text(json.dumps(chunks[0], ensure_ascii=False) + "\n")
            npz, meta = write_embeddings(tmp, vectors, ids, payload["meta"])
            build_index(
                chunks_path=chunks_path,
                embeddings_npz=npz,
                embeddings_meta_path=meta,
                index_dir=tmp / "index",
            )
            index = load_index(tmp / "index")
            rows = run_retrieval_sweep(
                index, emb, gold, modes=["bm25", "hybrid"], top_k=3
            )
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["metrics"]["recall_at_10"], 1.0)


if __name__ == "__main__":
    unittest.main()
