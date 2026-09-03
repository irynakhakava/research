"""Тесты шага 3: structure-aware chunking."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-1-data"))

from pipeline.chunking import chunk_document, chunk_text, iter_sections
from pipeline.config import REPO_ROOT, load_config
from pipeline.load import load_normalized_documents
from pipeline.chunking import chunk_documents


class TestChunking(unittest.TestCase):
    def test_config_chunking_defaults(self) -> None:
        cfg = load_config()
        self.assertEqual(cfg["chunking"]["strategy"], "structure_b")
        self.assertEqual(cfg["chunking"]["max_chars"], 1500)
        self.assertEqual(cfg["chunking"]["overlap"], 180)

    def test_sections_by_headings(self) -> None:
        text = "# Title\n\nintro\n\n## A\n\nbody a\n\n## B\n\nbody b\n"
        sections = iter_sections(text)
        self.assertGreaterEqual(len(sections), 2)
        paths = [" / ".join(p) for p, _ in sections]
        self.assertTrue(any("A" in p for p in paths))

    def test_does_not_split_code_fence(self) -> None:
        fence = "```bash\n" + ("echo hi\n" * 5) + "```\n"
        text = "# Doc\n\n## Steps\n\n" + fence + "\nafter\n"
        parts = chunk_text(text, max_chars=80, overlap=10, min_chars=5)
        joined = "\n".join(t for _, t in parts)
        # opening and closing fence counts should match in each chunk that has fences
        for _, chunk in parts:
            if "```" in chunk:
                self.assertEqual(chunk.count("```") % 2, 0, msg=chunk)

        self.assertIn("echo hi", joined)

    def test_chunk_ids_stable(self) -> None:
        doc = {
            "doc_id": "demo-doc",
            "source_id": "platform-confluence-runbooks",
            "title": "Demo",
            "text": "# Demo\n\n## One\n\nhello world\n\n## Two\n\nsecond section text\n",
            "acl": "team-only",
            "team": "platform",
            "priority": "p0",
            "language": "ru",
        }
        a, _ = chunk_document(doc, max_chars=1500, overlap=180, min_chars=40)
        b, _ = chunk_document(doc, max_chars=1500, overlap=180, min_chars=40)
        self.assertEqual([c["chunk_id"] for c in a], [c["chunk_id"] for c in b])
        self.assertTrue(a[0]["chunk_id"].endswith("::0000"))

    def test_metadata_copied_from_document(self) -> None:
        doc = {
            "doc_id": "demo-doc",
            "source_id": "sre-notion-incident-guides",
            "title": "Demo",
            "text": "# Demo\n\n## Section\n\n" + ("word " * 50) + "\n",
            "acl": "public-to-company",
            "team": "sre",
            "priority": "p0",
            "language": "ru",
        }
        chunks, _ = chunk_document(doc, max_chars=1500, overlap=180, min_chars=10)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["acl"], "public-to-company")
        self.assertEqual(chunks[0]["team"], "sre")
        self.assertIn("heading_path", chunks[0])

    def test_pipeline_p0_produces_chunks(self) -> None:
        cfg = load_config()
        docs, report = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=["p0"],
        )
        self.assertEqual(report["errors"], [])
        chunks, creport = chunk_documents(
            docs,
            max_chars=int(cfg["chunking"]["max_chars"]),
            overlap=int(cfg["chunking"]["overlap"]),
            min_chars=int(cfg["chunking"]["min_chars"]),
        )
        self.assertGreater(len(chunks), len(docs))
        self.assertEqual(creport["empty_docs"], [])
        # every p0 doc has at least one chunk
        doc_ids = {d["doc_id"] for d in docs}
        chunk_docs = {c["doc_id"] for c in chunks}
        self.assertEqual(doc_ids, chunk_docs)


if __name__ == "__main__":
    unittest.main()
