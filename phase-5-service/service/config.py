"""Конфиг фазы 5."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"
PHASE2_DIR = REPO_ROOT / "phase-2-retrieval"
PHASE3_DIR = REPO_ROOT / "phase-3-generation"

for extra in (PHASE2_DIR, PHASE3_DIR):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from retrieval.config import _parse_yaml  # noqa: E402


DEFAULT_EMBEDDINGS = {
    "backend": "sentence_transformers",
    "model_name": "intfloat/multilingual-e5-small",
    "batch_size": 16,
    "normalize": True,
    "passage_prefix": "passage: ",
    "query_prefix": "query: ",
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    data = _parse_yaml(cfg_path.read_text(encoding="utf-8"))
    emb = dict(DEFAULT_EMBEDDINGS)
    raw = data.get("embeddings") or {}
    if isinstance(raw, dict):
        emb.update(raw)
    for key in ("passage_prefix", "query_prefix"):
        prefix = str(emb.get(key, ""))
        if prefix and not prefix.endswith(" "):
            emb[key] = prefix + " "
    return {
        "index_dir": REPO_ROOT / data.get("index_dir", "data/processed/index"),
        "documents_path": REPO_ROOT
        / data.get("documents_path", "data/processed/documents.jsonl"),
        "catalog_path": REPO_ROOT
        / data.get("catalog_path", "phase-0-discovery/sources.catalog.yaml"),
        "gold_set_path": REPO_ROOT
        / data.get("gold_set_path", "phase-0-discovery/gold-set/dataset.jsonl"),
        "embeddings": emb,
        "retrieve": data.get("retrieve") if isinstance(data.get("retrieve"), dict) else {},
        "generation": data.get("generation") if isinstance(data.get("generation"), dict) else {},
        "server": data.get("server") if isinstance(data.get("server"), dict) else {},
        "config_path": cfg_path,
    }
