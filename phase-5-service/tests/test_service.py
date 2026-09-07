"""Тесты фазы 5: /search /ask /health + rebuild dry-run."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-5-service"))
sys.path.insert(0, str(ROOT / "phase-3-generation"))
sys.path.insert(0, str(ROOT / "phase-2-retrieval"))

from retrieval.embed_chunks import embed_chunks, write_embeddings
from retrieval.embedders import HashEmbedder
from retrieval.index import build_index, load_index
from service.app import AppContext, do_ask, do_search, health_payload
from service.loggingutil import new_trace_id


def _chunk(cid: str, doc_id: str, text: str, team: str = "platform") -> dict:
    return {
        "chunk_id": cid,
        "doc_id": doc_id,
        "source_id": "platform-confluence-runbooks",
        "text": text,
        "content_hash": "h-" + cid,
        "acl": "team-only",
        "team": team,
        "priority": "p0",
        "language": "ru",
        "heading_path": ["Rollback"],
        "char_count": len(text),
    }


class TestServiceHandlers(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        chunks = [
            _chunk(
                "plat::0002",
                "plat-runbook-payments-rollback",
                "rollback payments staging pipeline ARTIFACT_SHA",
            ),
            _chunk(
                "data::0000",
                "data-airflow-backfill",
                "airflow backfill dag retry",
                team="data",
            ),
        ]
        emb = HashEmbedder(dim=32)
        vectors, ids, payload = embed_chunks(chunks, emb)
        chunks_path = tmp / "chunks.jsonl"
        chunks_path.write_text(
            "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n"
        )
        npz, meta = write_embeddings(tmp, vectors, ids, payload["meta"])
        build_index(
            chunks_path=chunks_path,
            embeddings_npz=npz,
            embeddings_meta_path=meta,
            index_dir=tmp / "index",
        )
        docs_path = tmp / "documents.jsonl"
        docs_path.write_text(
            json.dumps(
                {
                    "doc_id": "plat-runbook-payments-rollback",
                    "path": "data/corpus/platform-confluence-runbooks/plat-runbook-payments-rollback.md",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self.ctx = AppContext(
            index=load_index(tmp / "index"),
            embedder=emb,
            retrieve={"mode": "hybrid", "top_k": 5, "candidate_k": 10, "rrf_k": 60},
            generation={
                "backend": "extractive",
                "model_name": "extractive",
                "max_context_chunks": 3,
                "min_dense_score": 0.0,
                "nearest_links": 2,
                "quote_chars": 80,
            },
            documents_by_id={
                "plat-runbook-payments-rollback": (
                    "data/corpus/platform-confluence-runbooks/"
                    "plat-runbook-payments-rollback.md"
                )
            },
            locations={},
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_health(self) -> None:
        payload = health_payload()
        self.assertTrue(payload["ok"])
        self.assertIn("POST /search", payload["endpoints"])

    def test_search_and_trace(self) -> None:
        code, body = do_search(
            self.ctx,
            {"question": "rollback payments staging"},
            trace_id="t-search-1",
        )
        self.assertEqual(code, 200)
        self.assertEqual(body["trace_id"], "t-search-1")
        self.assertGreaterEqual(len(body["hits"]), 1)
        self.assertEqual(body["hits"][0]["doc_id"], "plat-runbook-payments-rollback")

    def test_search_requires_question(self) -> None:
        code, body = do_search(self.ctx, {}, trace_id="t-empty")
        self.assertEqual(code, 400)
        self.assertIn("question", body["error"])

    def test_ask_refuse_secret(self) -> None:
        code, body = do_ask(
            self.ctx,
            {"question": "Какой пароль от прод-БД payments?"},
            trace_id="t-ask-secret",
        )
        self.assertEqual(code, 200)
        self.assertTrue(body["refuse"])
        self.assertEqual(body["trace_id"], "t-ask-secret")

    def test_acl_filter_on_search(self) -> None:
        code, body = do_search(
            self.ctx,
            {"question": "rollback payments", "team": "data"},
            trace_id="t-acl",
        )
        self.assertEqual(code, 200)
        self.assertTrue(all(h["team"] == "data" for h in body["hits"]))

    def test_trace_id_from_header(self) -> None:
        self.assertEqual(new_trace_id("abc"), "abc")
        self.assertTrue(len(new_trace_id(None)) > 8)


class TestRebuildDryRun(unittest.TestCase):
    def test_dry_run_exits_zero(self) -> None:
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(ROOT / "phase-5-service" / "run_rebuild.py"), "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("run_pipeline.py", proc.stdout)
        self.assertIn("dry-run", proc.stdout)


if __name__ == "__main__":
    unittest.main()
