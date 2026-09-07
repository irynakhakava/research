"""Загрузка phase-2-retrieval/config.yaml (минимальный парсер)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"

DEFAULT_EMBEDDINGS = {
    "backend": "sentence_transformers",
    "model_name": "intfloat/multilingual-e5-small",
    "batch_size": 16,
    "normalize": True,
    "passage_prefix": "passage: ",
    "query_prefix": "query: ",
}


def _coerce(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    return value.strip('"').strip("'")


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line


def _parse_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_map: str | None = None
    for raw in text.splitlines():
        raw = _strip_comment(raw)
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent >= 2 and current_map:
            key, _, value = raw.strip().partition(":")
            if value.strip() == "":
                continue
            nested = result.setdefault(current_map, {})
            if isinstance(nested, dict):
                val = value.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                if key.strip().endswith("_prefix"):
                    nested[key.strip()] = val
                else:
                    nested[key.strip()] = _coerce(val)
            continue
        current_map = None
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            current_map = key
            result[key] = {}
        else:
            result[key] = _coerce(value)
    return result


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    data = _parse_yaml(cfg_path.read_text(encoding="utf-8"))
    emb = dict(DEFAULT_EMBEDDINGS)
    raw = data.get("embeddings") or {}
    if isinstance(raw, dict):
        emb.update(raw)
    # ensure prefixes end with space if they look like e5 prefixes
    for key in ("passage_prefix", "query_prefix"):
        prefix = str(emb.get(key, ""))
        if prefix and not prefix.endswith(" "):
            emb[key] = prefix + " "
    eval_cfg: dict[str, Any] = {}
    raw_eval = data.get("eval")
    if isinstance(raw_eval, dict):
        eval_cfg = dict(raw_eval)
        ks = eval_cfg.get("k_values", [1, 5, 10])
        if isinstance(ks, str):
            eval_cfg["k_values"] = [int(x.strip()) for x in ks.split(",") if x.strip()]
        elif isinstance(ks, list):
            eval_cfg["k_values"] = [int(x) for x in ks]
        pri = eval_cfg.get("priorities", ["p0"])
        if isinstance(pri, str):
            eval_cfg["priorities"] = [x.strip() for x in pri.split(",") if x.strip()]
        elif isinstance(pri, list):
            eval_cfg["priorities"] = [str(x) for x in pri]

    return {
        "chunks_path": REPO_ROOT / data.get("chunks_path", "data/processed/chunks.jsonl"),
        "output_dir": REPO_ROOT / data.get("output_dir", "data/processed"),
        "index_dir": REPO_ROOT / data.get("index_dir", "data/processed/index"),
        "gold_set_path": REPO_ROOT
        / data.get("gold_set_path", "phase-0-discovery/gold-set/dataset.jsonl"),
        "embeddings": emb,
        "index": data.get("index") if isinstance(data.get("index"), dict) else {},
        "retrieve": data.get("retrieve") if isinstance(data.get("retrieve"), dict) else {},
        "eval": eval_cfg,
        "config_path": cfg_path,
    }
