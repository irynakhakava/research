"""Smoke-тесты шагов 1–2."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-1-data"))

from pipeline.catalog import filter_sources_by_priority, load_catalog
from pipeline.config import REPO_ROOT, load_config
from pipeline.load import load_normalized_documents
from pipeline.normalize import build_document, parse_frontmatter


class TestSteps12(unittest.TestCase):
    def test_config_default_p0_only(self) -> None:
        cfg = load_config()
        self.assertEqual(cfg["priorities"], ["p0"])

    def test_catalog_has_p0_sources(self) -> None:
        cfg = load_config()
        catalog = load_catalog(cfg["catalog_path"])
        scoped = filter_sources_by_priority(catalog, ["p0"])
        self.assertIn("platform-confluence-runbooks", scoped)
        self.assertEqual(scoped["platform-confluence-runbooks"].team, "platform")
        self.assertEqual(scoped["platform-confluence-runbooks"].acl, "team-only")
        # p1 не должен попасть
        self.assertNotIn("security-policies", scoped)

    def test_frontmatter_split(self) -> None:
        raw = "---\nid: demo\ntitle: Hello\n---\n\n# Hello\n\nbody\n"
        meta, body = parse_frontmatter(raw)
        self.assertEqual(meta["id"], "demo")
        self.assertTrue(body.startswith("# Hello"))

    def test_load_p0_documents(self) -> None:
        cfg = load_config()
        docs, report = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=["p0"],
        )
        self.assertEqual(report["errors"], [])
        self.assertGreaterEqual(len(docs), 1)
        # p1 docs должны быть отфильтрованы
        self.assertNotIn("sec-policy-pii-logging", {d["doc_id"] for d in docs})
        sample = next(d for d in docs if d["doc_id"] == "plat-runbook-payments-rollback")
        self.assertEqual(sample["acl"], "team-only")
        self.assertEqual(sample["team"], "platform")
        self.assertEqual(sample["priority"], "p0")
        self.assertTrue(sample["content_hash"].startswith("sha256:"))
        self.assertNotIn("---\n", sample["text"][:10])
        self.assertIn("rollback", sample["text"].lower())

    def test_p1_included_when_requested(self) -> None:
        cfg = load_config()
        docs, _ = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=["p0", "p1"],
        )
        ids = {d["doc_id"] for d in docs}
        self.assertIn("sec-policy-pii-logging", ids)

    def test_doc_id_mismatch_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_document(
                path_rel="data/corpus/x/wrong-name.md",
                raw_markdown="---\nid: other-id\nsource_id: x\n---\n\n# t\n",
                source_id="x",
                acl="team-only",
                team="platform",
                priority="p0",
                doc_types=["runbook"],
            )


if __name__ == "__main__":
    unittest.main()
