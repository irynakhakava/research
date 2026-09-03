"""Нормализация markdown: frontmatter → поля, body → text, hash."""

from __future__ import annotations

import hashlib
import re
from typing import Any

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Вернуть (frontmatter_fields, body_markdown)."""
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw.strip() + ("\n" if raw.strip() else "")

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")

    body = match.group(2).strip() + "\n"
    return meta, body


def content_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def title_from_body(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_document(
    *,
    path_rel: str,
    raw_markdown: str,
    source_id: str,
    acl: str,
    team: str,
    priority: str,
    doc_types: list[str],
    default_language: str = "ru",
) -> dict[str, Any]:
    """Собрать нормализованный документ по контракту шага 2."""
    meta, text = parse_frontmatter(raw_markdown)
    file_stem = path_rel.rsplit("/", 1)[-1].removesuffix(".md")

    doc_id = meta.get("id") or file_stem
    if doc_id != file_stem:
        raise ValueError(
            f"doc_id mismatch: frontmatter id={doc_id!r} vs filename stem={file_stem!r} ({path_rel})"
        )
    if meta.get("source_id") and meta["source_id"] != source_id:
        raise ValueError(
            f"source_id mismatch in {path_rel}: frontmatter={meta['source_id']!r} folder/catalog={source_id!r}"
        )

    title = meta.get("title") or title_from_body(text, fallback=doc_id)
    language = meta.get("language") or default_language
    digest = content_hash(text)

    return {
        "doc_id": doc_id,
        "source_id": source_id,
        "title": title,
        "path": path_rel,
        "text": text,
        "language": language,
        "acl": acl,
        "team": team,
        "priority": priority,
        "doc_types": list(doc_types),
        "content_hash": digest,
        "char_count": len(text),
        "updated_at": meta.get("updated_at") or "",
    }
