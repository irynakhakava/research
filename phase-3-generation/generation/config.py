"""Загрузка phase-3-generation/config.yaml (минимальный парсер, тот же стиль что фаза 2)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"
PHASE2_DIR = REPO_ROOT / "phase-2-retrieval"

if str(PHASE2_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE2_DIR))

from retrieval.config import _parse_yaml  # noqa: E402


DEFAULT_EMBEDDINGS = {
    "backend": "sentence_transformers",
    "model_name": "intfloat/multilingual-e5-small",
    "batch_size": 16,
    "normalize": True,
    "passage_prefix": "passage: ",
    "query_prefix": "query: ",
}

DEFAULT_GENERATION = {
    "backend": "extractive",
    "model_name": "extractive",
    "max_context_chunks": 4,
    "min_dense_score": 0.28,
    "refuse_policy": "refuse_with_nearest_links",
    "nearest_links": 3,
    "quote_chars": 280,
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o-mini",
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

    gen = dict(DEFAULT_GENERATION)
    raw_gen = data.get("generation") or {}
    if isinstance(raw_gen, dict):
        gen.update(raw_gen)

    return {
        "index_dir": REPO_ROOT / data.get("index_dir", "data/processed/index"),
        "documents_path": REPO_ROOT
        / data.get("documents_path", "data/processed/documents.jsonl"),
        "catalog_path": REPO_ROOT
        / data.get("catalog_path", "phase-0-discovery/sources.catalog.yaml"),
        "gold_set_path": REPO_ROOT
        / data.get("gold_set_path", "phase-0-discovery/gold-set/dataset.jsonl"),
        "output_dir": REPO_ROOT / data.get("output_dir", "data/processed"),
        "embeddings": emb,
        "retrieve": data.get("retrieve") if isinstance(data.get("retrieve"), dict) else {},
        "generation": gen,
        "eval": data.get("eval") if isinstance(data.get("eval"), dict) else {},
        "server": data.get("server") if isinstance(data.get("server"), dict) else {},
        "config_path": cfg_path,
    }
