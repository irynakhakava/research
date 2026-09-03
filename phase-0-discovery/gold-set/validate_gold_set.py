#!/usr/bin/env python3
"""Валидатор gold-set для фазы 0 Discovery.

Проверяет dataset.jsonl (или переданный путь) без внешних зависимостей.
Схема-источник правды для людей: schema.json; здесь — практические инварианты.

Использование:
  python phase-0-discovery/gold-set/validate_gold_set.py
  python phase-0-discovery/gold-set/validate_gold_set.py path/to/file.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

QUERY_TYPES = {"how-to", "troubleshooting", "where-is", "concept", "policy"}
BEHAVIORS = {"answer", "refuse"}
PRIORITIES = {"p0", "p1"}
LANGUAGES = {"ru", "en", "mixed"}
ID_RE = re.compile(r"^q-[a-z0-9-]+$")

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "dataset.jsonl"
CATALOG_PATH = ROOT.parent / "sources.catalog.yaml"


def load_catalog_ids() -> set[str] | None:
    """Грубый парсер id источников из YAML-каталога без PyYAML.

    Читает только блок `sources:` (игнорирует `teams:` и др.).
    """
    if not CATALOG_PATH.exists():
        return None
    ids: set[str] = set()
    in_sources = False
    for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("sources:"):
            in_sources = True
            continue
        if in_sources and line and not line.startswith(" ") and not line.startswith("\t") and not line.startswith("#"):
            # следующий top-level ключ — выходим из блока sources
            if line.rstrip().endswith(":") or ":" in line:
                break
        if not in_sources:
            continue
        stripped = line.strip()
        if stripped.startswith("- id:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            if value:
                ids.add(value)
    return ids


def validate_item(
    item: object,
    line_no: int,
    catalog_ids: set[str] | None,
) -> list[str]:
    errors: list[str] = []

    def err(msg: str) -> None:
        errors.append(f"L{line_no}: {msg}")

    if not isinstance(item, dict):
        err("ожидался JSON-объект")
        return errors

    required = [
        "id",
        "question",
        "query_type",
        "expected_behavior",
        "relevant_doc_ids",
        "source_priority",
    ]
    for key in required:
        if key not in item:
            err(f"нет обязательного поля '{key}'")

    case_id = item.get("id")
    if isinstance(case_id, str):
        if not ID_RE.match(case_id):
            err("id должен матчить ^q-[a-z0-9-]+$")
    elif "id" in item:
        err("id должен быть строкой")

    question = item.get("question")
    if isinstance(question, str):
        if len(question.strip()) < 5:
            err("question слишком короткий")
    elif "question" in item:
        err("question должен быть строкой")

    query_type = item.get("query_type")
    if query_type not in QUERY_TYPES and "query_type" in item:
        err(f"query_type должен быть одним из {sorted(QUERY_TYPES)}")

    behavior = item.get("expected_behavior")
    if behavior not in BEHAVIORS and "expected_behavior" in item:
        err(f"expected_behavior должен быть одним из {sorted(BEHAVIORS)}")

    priority = item.get("source_priority")
    if priority not in PRIORITIES and "source_priority" in item:
        err(f"source_priority должен быть одним из {sorted(PRIORITIES)}")

    docs = item.get("relevant_doc_ids")
    if "relevant_doc_ids" in item and not isinstance(docs, list):
        err("relevant_doc_ids должен быть массивом")
    elif isinstance(docs, list) and not all(isinstance(x, str) and x.strip() for x in docs):
        err("relevant_doc_ids: все элементы — непустые строки")

    if behavior == "answer":
        if isinstance(docs, list) and len(docs) < 1:
            err("для expected_behavior=answer нужен хотя бы 1 relevant_doc_ids")
        primary = item.get("primary_doc_id")
        if not isinstance(primary, str) or not primary.strip():
            err("для expected_behavior=answer нужен primary_doc_id")
        elif isinstance(docs, list) and primary not in docs:
            err("primary_doc_id должен входить в relevant_doc_ids")

    if behavior == "refuse" and isinstance(docs, list) and len(docs) > 0:
        # Разрешаем непустой список (например «документы, которых недостаточно»),
        # но предупреждение полезнее ошибки — оставляем мягко через notes.
        pass

    source_ids = item.get("source_ids")
    if source_ids is not None:
        if not isinstance(source_ids, list) or not all(isinstance(x, str) for x in source_ids):
            err("source_ids должен быть массивом строк")
        elif catalog_ids is not None:
            unknown = [x for x in source_ids if x not in catalog_ids]
            if unknown:
                err(f"source_ids не найдены в sources.catalog.yaml: {unknown}")

    language = item.get("language")
    if language is not None and language not in LANGUAGES:
        err(f"language должен быть одним из {sorted(LANGUAGES)}")

    unknown_keys = set(item) - {
        "id",
        "question",
        "query_type",
        "expected_behavior",
        "relevant_doc_ids",
        "primary_doc_id",
        "source_ids",
        "source_priority",
        "reference_answer",
        "notes",
        "tags",
        "language",
    }
    if unknown_keys:
        err(f"неизвестные поля: {sorted(unknown_keys)}")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    if not path.exists():
        print(f"FAIL: файл не найден: {path}")
        return 1

    catalog_ids = load_catalog_ids()
    errors: list[str] = []
    ids: list[str] = []
    types: Counter[str] = Counter()
    behaviors: Counter[str] = Counter()
    count = 0

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        count += 1
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"L{line_no}: невалидный JSON ({exc})")
            continue

        errors.extend(validate_item(item, line_no, catalog_ids))
        if isinstance(item, dict):
            case_id = item.get("id")
            if isinstance(case_id, str):
                ids.append(case_id)
            qt = item.get("query_type")
            if isinstance(qt, str):
                types[qt] += 1
            beh = item.get("expected_behavior")
            if isinstance(beh, str):
                behaviors[beh] += 1

    dupes = [case_id for case_id, n in Counter(ids).items() if n > 1]
    if dupes:
        errors.append(f"дублирующиеся id: {dupes}")

    print(f"Файл: {path}")
    print(f"Кейсов: {count}")
    print(f"query_type: {dict(types)}")
    print(f"expected_behavior: {dict(behaviors)}")
    if catalog_ids is not None:
        print(f"Источник ids в каталоге: {len(catalog_ids)}")

    distinct_types = len(types)
    refuse_n = behaviors.get("refuse", 0)

    warnings: list[str] = []
    if count < 30:
        warnings.append(
            f"пока {count} кейсов — для завершения фазы 0 желательно ≥ 30 "
            "(к экспериментам 50–150)"
        )
    if distinct_types < 3:
        warnings.append("нужно ≥ 3 разных query_type")
    if refuse_n < 1:
        warnings.append("добавьте хотя бы 1 кейс с expected_behavior=refuse")

    for warning in warnings:
        print(f"WARN: {warning}")

    if errors:
        print(f"\nFAIL: {len(errors)} ошибок")
        for message in errors:
            print(f"  - {message}")
        return 1

    print("\nOK: gold-set валиден")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
