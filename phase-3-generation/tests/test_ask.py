"""Тесты фазы 3: refuse, citations, extractive /ask."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-3-generation"))
sys.path.insert(0, str(ROOT / "phase-2-retrieval"))

from generation.ask import ask
from generation.citations import build_citations, citation_url, load_source_locations
from generation.eval import citation_ok, grounded_ok
from generation.refuse import classify_query_refuse
from retrieval.embed_chunks import embed_chunks, write_embeddings
from retrieval.embedders import HashEmbedder
from retrieval.index import build_index, load_index
from retrieval.retrieve import SearchHit


def _chunk(chunk_id: str, doc_id: str, text: str, team: str = "platform") -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "source_id": "platform-confluence-runbooks",
        "text": text,
        "content_hash": "h-" + chunk_id,
        "acl": "team-only",
        "team": team,
        "priority": "p0",
        "language": "ru",
        "heading_path": ["Runbook", "Staging"],
        "char_count": len(text),
    }


class TestRefuseAndCitations(unittest.TestCase):
    def test_secret_and_oos_patterns(self) -> None:
        self.assertEqual(
            classify_query_refuse("Какой пароль от прод-БД payments?"),
            "secret",
        )
        self.assertEqual(
            classify_query_refuse("Какая зарплата у CEO NordLedger?"),
            "secret",
        )
        self.assertEqual(
            classify_query_refuse("Когда Иванов выйдет из отпуска?"),
            "out_of_scope",
        )
        self.assertIsNone(classify_query_refuse("Как откатить payments в staging?"))

    def test_citation_has_path_and_url(self) -> None:
        hits = [
            SearchHit(
                "plat::0002",
                0.9,
                "plat-runbook-payments-rollback",
                "platform-confluence-runbooks",
                "platform",
                "team-only",
                ["Staging"],
                "## Staging rollback\njob rollback:staging",
            )
        ]
        cits = build_citations(
            hits,
            documents_by_id={
                "plat-runbook-payments-rollback": (
                    "data/corpus/platform-confluence-runbooks/"
                    "plat-runbook-payments-rollback.md"
                )
            },
            locations={
                "platform-confluence-runbooks": (
                    "https://wiki.nordledger.example/spaces/PLAT"
                )
            },
        )
        self.assertEqual(len(cits), 1)
        self.assertTrue(cits[0].path.endswith(".md"))
        self.assertIn("wiki.nordledger.example", cits[0].url)
        self.assertIn("plat-runbook-payments-rollback", cits[0].url)

    def test_catalog_locations_parse(self) -> None:
        locs = load_source_locations(
            ROOT / "phase-0-discovery" / "sources.catalog.yaml"
        )
        self.assertIn("platform-confluence-runbooks", locs)
        self.assertTrue(locs["platform-confluence-runbooks"].startswith("http"))
        self.assertTrue(
            citation_url("unknown", "doc-x", {}).startswith("nordledger://")
        )


class TestAskPipeline(unittest.TestCase):
    def _index(self, tmp: Path):
        chunks = [
            _chunk(
                "plat-runbook-payments-rollback::0002",
                "plat-runbook-payments-rollback",
                "Как откатить релиз payments staging rollback pipeline ARTIFACT_SHA",
            ),
            _chunk(
                "other::0000",
                "other-doc",
                "celery queue metrics unrelated airflow",
                team="data",
            ),
        ]
        emb = HashEmbedder(dim=32)
        vectors, ids, payload = embed_chunks(chunks, emb)
        chunks_path = tmp / "chunks.jsonl"
        chunks_path.write_text(
            "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n",
            encoding="utf-8",
        )
        npz, meta = write_embeddings(tmp, vectors, ids, payload["meta"])
        index_dir = tmp / "index"
        build_index(
            chunks_path=chunks_path,
            embeddings_npz=npz,
            embeddings_meta_path=meta,
            index_dir=index_dir,
        )
        return load_index(index_dir), emb, {
            "plat-runbook-payments-rollback": (
                "data/corpus/platform-confluence-runbooks/"
                "plat-runbook-payments-rollback.md"
            ),
            "other-doc": "data/corpus/x/other-doc.md",
        }

    def test_extractive_answer_has_citations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            index, emb, docs = self._index(tmp)
            resp = ask(
                index,
                emb,
                "rollback payments staging",
                documents_by_id=docs,
                locations={"platform-confluence-runbooks": "https://wiki.example/runbooks"},
                mode="hybrid",
                min_dense_score=0.0,
                generation_backend="extractive",
            )
            self.assertFalse(resp.refuse)
            self.assertTrue(resp.citations)
            self.assertTrue(all(c.path for c in resp.citations))
            self.assertIn("[1]", resp.answer)
            self.assertTrue(citation_ok(resp))
            self.assertTrue(
                grounded_ok(resp, ["plat-runbook-payments-rollback"])
            )

    def test_secret_refuses_with_nearest_links(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            index, emb, docs = self._index(tmp)
            resp = ask(
                index,
                emb,
                "Какой пароль от прод-БД payments?",
                documents_by_id=docs,
                locations={},
                mode="hybrid",
                min_dense_score=0.0,
            )
            self.assertTrue(resp.refuse)
            self.assertEqual(resp.refuse_reason, "secret")
            self.assertIn("секрет", resp.answer.lower())
            # nearest links allowed
            self.assertTrue(len(resp.citations) <= 3)
            if resp.citations:
                self.assertTrue(all(c.path for c in resp.citations))

    def test_acl_filter_does_not_leak(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            index, emb, docs = self._index(tmp)
            resp = ask(
                index,
                emb,
                "rollback payments staging",
                documents_by_id=docs,
                locations={},
                mode="hybrid",
                team="data",
                min_dense_score=0.0,
            )
            self.assertTrue(all(c.doc_id != "plat-runbook-payments-rollback" for c in resp.citations))
            leaked = any(
                cid.startswith("plat-runbook-payments-rollback")
                for cid in resp.retrieved_chunk_ids
            )
            self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
