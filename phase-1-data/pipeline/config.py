"""Загрузка phase-1-data/config.yaml (минимальный YAML, без PyYAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"

DEFAULT_CHUNKING = {
    "strategy": "structure_b",
    "max_chars": 1500,
    "overlap": 180,
    "min_chars": 40,
}


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Парсер под наш config.yaml (top-level + один уровень вложенности + списки)."""
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    current_map_key: str | None = None

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))

        if indent >= 2 and current_map_key:
            stripped = raw.strip()
            if stripped.startswith("- "):
                # list under nested map not used in our config
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                nested = result.setdefault(current_map_key, {})
                if isinstance(nested, dict):
                    if value == "":
                        nested[key] = {}
                    else:
                        nested[key] = _coerce_scalar(value)
            continue

        if indent >= 2 and current_list_key:
            item = raw.strip()
            if item.startswith("- "):
                result.setdefault(current_list_key, []).append(item[2:].strip())
            continue

        current_list_key = None
        current_map_key = None

        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            # could be list or nested map — look ahead is hard; default to list,
            # but chunking: uses nested map. Detect by known keys.
            if key == "chunking":
                current_map_key = key
                result[key] = {}
            else:
                current_list_key = key
                result[key] = []
        else:
            result[key] = _coerce_scalar(value.strip('"').strip("'"))
    return result


def _coerce_scalar(value: str) -> Any:
    if value.isdigit():
        return int(value)
    try:
        if "." in value:
            return float(value)
    except ValueError:
        pass
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    data = _parse_simple_yaml(cfg_path.read_text(encoding="utf-8"))
    priorities = data.get("priorities") or ["p0"]
    if isinstance(priorities, str):
        priorities = [priorities]

    chunking = dict(DEFAULT_CHUNKING)
    raw_chunking = data.get("chunking") or {}
    if isinstance(raw_chunking, dict):
        chunking.update(raw_chunking)

    return {
        "corpus_root": REPO_ROOT / data.get("corpus_root", "data/corpus"),
        "catalog_path": REPO_ROOT / data.get(
            "catalog_path", "phase-0-discovery/sources.catalog.yaml"
        ),
        "gold_set_path": REPO_ROOT
        / data.get("gold_set_path", "phase-0-discovery/gold-set/dataset.jsonl"),
        "output_dir": REPO_ROOT / data.get("output_dir", "data/processed"),
        "priorities": list(priorities),
        "exclude_priorities": list(data.get("exclude_priorities") or ["exclude"]),
        "chunking": chunking,
        "config_path": cfg_path,
    }
