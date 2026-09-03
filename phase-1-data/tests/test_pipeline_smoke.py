"""Шаг 6: smoke-тесты пайплайна и quality (шаг 5)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase-1-data"))

from pipeline.chunking import chunk_documents
from pipeline.config import REPO_ROOT, load_config
from pipeline.load import load_normalized_documents
from pipeline.quality import (
    check_goldset_coverage,
    check_orphans,
    p0_relevant_doc_ids,
    run_quality_checks,
    load_gold_set,
)


class TestPipelineSmoke(unittest.TestCase):
    def test_load_joins_catalog(self) -> None:
        cfg = load_config()
        docs, report = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=["p0"],
        )
        self.assertEqual(report["errors"], [])
        sample = next(d for d in docs if d["doc_id"] == "plat-runbook-payments-rollback")
        self.assertEqual(sample["team"], "platform")
        self.assertEqual(sample["acl"], "team-only")

    def test_p0_only_default(self) -> None:
        cfg = load_config()
        self.assertEqual(cfg["priorities"], ["p0"])
        docs, _ = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=cfg["priorities"],
        )
        self.assertTrue(all(d["priority"] == "p0" for d in docs))
        self.assertNotIn("sec-policy-pii-logging", {d["doc_id"] for d in docs})

    def test_goldset_p0_docs_present(self) -> None:
        cfg = load_config()
        docs, _ = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=["p0"],
        )
        result = check_goldset_coverage(
            docs, cfg["gold_set_path"], priorities=["p0"]
        )
        self.assertTrue(result["ok"], msg=result.get("missing_doc_ids"))
        self.assertGreater(result["required_count"], 0)

    def test_orphans_and_quality_ok(self) -> None:
        cfg = load_config()
        docs, _ = load_normalized_documents(
            repo_root=REPO_ROOT,
            corpus_root=cfg["corpus_root"],
            catalog_path=cfg["catalog_path"],
            priorities=["p0"],
        )
        chunks, creport = chunk_documents(
            docs,
            max_chars=int(cfg["chunking"]["max_chars"]),
            overlap=int(cfg["chunking"]["overlap"]),
            min_chars=int(cfg["chunking"]["min_chars"]),
        )
        self.assertIn("chunks_dropped_empty", creport)
        orphans = check_orphans(docs, chunks)
        self.assertTrue(orphans["ok"], msg=orphans["orphan_doc_ids"])
        quality = run_quality_checks(
            documents=docs,
            chunks=chunks,
            gold_path=cfg["gold_set_path"],
            priorities=["p0"],
        )
        self.assertTrue(quality["ok"], msg=quality)

    def test_run_pipeline_cli(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "phase-1-data" / "run_pipeline.py"), "--dry-run"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr + proc.stdout)
        # stdout содержит JSON report
        self.assertIn('"quality"', proc.stdout)
        self.assertIn('"ok": true', proc.stdout.replace("True", "true"))

    def test_p0_relevant_ids_nonempty(self) -> None:
        cfg = load_config()
        items = load_gold_set(cfg["gold_set_path"])
        ids = p0_relevant_doc_ids(items)
        self.assertIn("plat-runbook-payments-rollback", ids)


if __name__ == "__main__":
    unittest.main()
