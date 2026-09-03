"""Чтение sources.catalog.yaml → метаданные источников (без PyYAML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceMeta:
    source_id: str
    priority: str
    acl: str
    team: str
    doc_types: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    name: str = ""


def _parse_flow_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip('"').strip("'") for part in inner.split(",")]
    return [value.strip('"').strip("'")]


def load_catalog(path: Path) -> dict[str, SourceMeta]:
    """Вернуть map source_id → SourceMeta только для блока sources:."""
    sources: dict[str, SourceMeta] = {}
    in_sources = False
    current: dict[str, object] | None = None
    in_owner = False

    def flush() -> None:
        nonlocal current
        if not current or "id" not in current:
            current = None
            return
        sid = str(current["id"])
        sources[sid] = SourceMeta(
            source_id=sid,
            priority=str(current.get("priority", "")),
            acl=str(current.get("acl", "")),
            team=str(current.get("team", "")),
            doc_types=list(current.get("doc_types") or []),  # type: ignore[arg-type]
            languages=list(current.get("languages") or []),  # type: ignore[arg-type]
            name=str(current.get("name", "")),
        )
        current = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("sources:"):
            in_sources = True
            continue
        if in_sources and raw and not raw.startswith((" ", "\t", "#")):
            flush()
            break
        if not in_sources:
            continue

        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- id:"):
            flush()
            current = {"id": stripped.split(":", 1)[1].strip().strip('"').strip("'")}
            in_owner = False
            continue

        if current is None:
            continue

        # выход из owner: при следующем ключе того же уровня, что и owner
        indent = len(raw) - len(raw.lstrip(" "))
        if in_owner and indent <= 4 and not stripped.startswith("-") and ":" in stripped:
            # ключи source-level имеют indent 4
            if not stripped.startswith("team:") and not stripped.startswith("contact:"):
                in_owner = False

        if stripped == "owner:" or stripped.startswith("owner:"):
            in_owner = True
            continue

        if in_owner and stripped.startswith("team:"):
            current["team"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            continue

        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if key == "priority":
            current["priority"] = value
        elif key == "acl":
            current["acl"] = value
        elif key == "name":
            current["name"] = value.strip('"').strip("'")
        elif key == "doc_types" and value:
            current["doc_types"] = _parse_flow_list(value)
        elif key == "languages" and value:
            current["languages"] = _parse_flow_list(value)

    flush()
    return sources


def filter_sources_by_priority(
    catalog: dict[str, SourceMeta],
    priorities: list[str],
    exclude_priorities: list[str] | None = None,
) -> dict[str, SourceMeta]:
    exclude = set(exclude_priorities or ["exclude"])
    allowed = set(priorities)
    return {
        sid: meta
        for sid, meta in catalog.items()
        if meta.priority in allowed and meta.priority not in exclude
    }
