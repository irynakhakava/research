"""Конфиг фазы 4 (сетка экспериментов)."""

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


def _split_csv(raw: Any, cast=str) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [cast(x) for x in raw]
    return [cast(x.strip()) for x in str(raw).split(",") if str(x).strip()]


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    data = _parse_yaml(cfg_path.read_text(encoding="utf-8"))
    exp = data.get("experiments") if isinstance(data.get("experiments"), dict) else {}
    return {
        "index_dir": REPO_ROOT / data.get("index_dir", "data/processed/index"),
        "documents_path": REPO_ROOT
        / data.get("documents_path", "data/processed/documents.jsonl"),
        "catalog_path": REPO_ROOT
        / data.get("catalog_path", "phase-0-discovery/sources.catalog.yaml"),
        "gold_set_path": REPO_ROOT
        / data.get("gold_set_path", "phase-0-discovery/gold-set/dataset.jsonl"),
        "output_dir": REPO_ROOT
        / data.get("output_dir", "data/processed/experiments"),
        "embeddings": data.get("embeddings") if isinstance(data.get("embeddings"), dict) else {},
        "retrieve": data.get("retrieve") if isinstance(data.get("retrieve"), dict) else {},
        "generation": data.get("generation") if isinstance(data.get("generation"), dict) else {},
        "experiments": {
            "retrieval_modes": _split_csv(exp.get("retrieval_modes", "hybrid,dense,bm25")),
            "ask_min_dense_scores": _split_csv(
                exp.get("ask_min_dense_scores", "0.20,0.28,0.40"), float
            ),
            "ask_top_ks": _split_csv(exp.get("ask_top_ks", "3,5"), int),
            "include_openai": str(exp.get("include_openai", "false")).lower() == "true",
        },
        "config_path": cfg_path,
    }
