"""Шаг 3: structure-aware chunking (strategy B).

Алгоритм:
1. Режем текст по заголовкам ## / ### (H1 идёт в heading_path).
2. Секцию длиннее max_chars дробим по абзацам с overlap.
3. Блоки ```...``` не разрываем посередине.
4. Чанки короче min_chars отбрасываем (кроме единственного чанка документа).
"""

from __future__ import annotations

import re
from typing import Any

from .normalize import content_hash

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def _split_preserving_fences(text: str) -> list[str]:
    """Разбить на абзацы, но code fence держать одним блоком."""
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    buf: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        block = "".join(buf).strip("\n")
        if block.strip():
            blocks.append(block)
        buf = []

    for line in lines:
        if line.lstrip().startswith("```"):
            if not in_fence:
                flush()
                in_fence = True
                buf.append(line)
            else:
                buf.append(line)
                in_fence = False
                flush()
            continue

        if in_fence:
            buf.append(line)
            continue

        if line.strip() == "":
            flush()
        else:
            buf.append(line)

    flush()
    return blocks


def _split_oversized(section_text: str, max_chars: int, overlap: int) -> list[str]:
    """Если секция больше max_chars — режем по абзацам с overlap."""
    if len(section_text) <= max_chars:
        return [section_text]

    paragraphs = _split_preserving_fences(section_text)
    if not paragraphs:
        return [section_text[:max_chars]]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def current_text() -> str:
        return "\n\n".join(current).strip()

    for para in paragraphs:
        para_len = len(para)
        # Огромный одиночный блок (длинный fence) — режем жёстко по max_chars,
        # стараясь не оставлять открытый fence без закрытия в том же куске.
        if para_len > max_chars and not current:
            start = 0
            while start < para_len:
                end = min(start + max_chars, para_len)
                piece = para[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end >= para_len:
                    break
                start = max(end - overlap, start + 1)
            continue

        added = para_len + (2 if current else 0)
        if current and current_len + added > max_chars:
            chunks.append(current_text())
            # overlap: хвост предыдущего текста
            tail = current_text()[-overlap:] if overlap > 0 else ""
            current = [tail.strip(), para] if tail.strip() else [para]
            current_len = len(current_text())
        else:
            current.append(para)
            current_len = len(current_text())

    if current:
        chunks.append(current_text())
    return chunks


def iter_sections(text: str) -> list[tuple[list[str], str]]:
    """Вернуть список (heading_path, section_body)."""
    lines = text.splitlines()
    h1 = ""
    h2 = ""
    h3 = ""
    buf: list[str] = []
    sections: list[tuple[list[str], str]] = []
    in_fence = False

    def path() -> list[str]:
        parts = [p for p in (h1, h2, h3) if p]
        return parts

    def flush() -> None:
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            sections.append((path(), body))
        buf = []

    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            buf.append(line)
            continue
        if in_fence:
            buf.append(line)
            continue

        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            flush()
            if level == 1:
                h1, h2, h3 = title, "", ""
            elif level == 2:
                h2, h3 = title, ""
            else:
                h3 = title
            # заголовок включаем в тело секции — иначе чанк теряет якорь
            buf.append(line)
            continue

        buf.append(line)

    flush()

    if not sections and text.strip():
        sections.append(([], text.strip()))
    return sections


def chunk_text(
    text: str,
    *,
    max_chars: int = 1500,
    overlap: int = 180,
    min_chars: int = 40,
) -> list[tuple[list[str], str]]:
    """Вернуть список (heading_path, chunk_text)."""
    raw_parts: list[tuple[list[str], str]] = []
    for heading_path, body in iter_sections(text):
        for piece in _split_oversized(body, max_chars=max_chars, overlap=overlap):
            piece = piece.strip()
            if piece:
                raw_parts.append((heading_path, piece))

    if not raw_parts:
        return []

    # drop tiny chunks, but keep at least one if document was non-empty
    kept = [(hp, t) for hp, t in raw_parts if len(t) >= min_chars]
    if not kept:
        kept = [raw_parts[0]]
    return kept


def chunk_text_with_stats(
    text: str,
    *,
    max_chars: int = 1500,
    overlap: int = 180,
    min_chars: int = 40,
) -> tuple[list[tuple[list[str], str]], int]:
    """Как chunk_text, плюс число отброшенных short-чанков."""
    # сырые секции до min_chars filter
    raw_parts: list[tuple[list[str], str]] = []
    for heading_path, body in iter_sections(text):
        for piece in _split_oversized(body, max_chars=max_chars, overlap=overlap):
            piece = piece.strip()
            if piece:
                raw_parts.append((heading_path, piece))
    if not raw_parts:
        return [], 0
    kept = [(hp, t) for hp, t in raw_parts if len(t) >= min_chars]
    dropped = len(raw_parts) - len(kept)
    if not kept:
        return [raw_parts[0]], max(0, len(raw_parts) - 1)
    return kept, dropped


def chunk_document(
    document: dict[str, Any],
    *,
    max_chars: int = 1500,
    overlap: int = 180,
    min_chars: int = 40,
) -> tuple[list[dict[str, Any]], int]:
    """Превратить document в chunks + число dropped short."""
    parts, dropped = chunk_text_with_stats(
        document["text"],
        max_chars=max_chars,
        overlap=overlap,
        min_chars=min_chars,
    )
    chunks: list[dict[str, Any]] = []
    for index, (heading_path, text) in enumerate(parts):
        path = list(heading_path) if heading_path else [
            document.get("title") or document["doc_id"]
        ]
        normalized = text if text.endswith("\n") else text + "\n"
        chunks.append(
            {
                "chunk_id": f"{document['doc_id']}::{index:04d}",
                "doc_id": document["doc_id"],
                "source_id": document["source_id"],
                "chunk_index": index,
                "text": normalized,
                "heading_path": path,
                "char_count": len(normalized),
                "acl": document["acl"],
                "team": document["team"],
                "priority": document["priority"],
                "language": document["language"],
                "content_hash": content_hash(normalized),
            }
        )
    return chunks, dropped


def chunk_documents(
    documents: list[dict[str, Any]],
    *,
    max_chars: int = 1500,
    overlap: int = 180,
    min_chars: int = 40,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_chunks: list[dict[str, Any]] = []
    by_source: dict[str, int] = {}
    empty_docs: list[str] = []
    dropped_empty = 0

    for doc in documents:
        chunks, dropped = chunk_document(
            doc,
            max_chars=max_chars,
            overlap=overlap,
            min_chars=min_chars,
        )
        dropped_empty += dropped
        if not chunks:
            empty_docs.append(doc["doc_id"])
            continue
        all_chunks.extend(chunks)
        sid = doc["source_id"]
        by_source[sid] = by_source.get(sid, 0) + len(chunks)

    # exact dedupe by content_hash (keep first chunk_id)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    deduped_count = 0
    for chunk in all_chunks:
        h = chunk["content_hash"]
        if h in seen:
            deduped_count += 1
            continue
        seen.add(h)
        deduped.append(chunk)

    report = {
        "strategy": "structure_b",
        "max_chars": max_chars,
        "overlap": overlap,
        "min_chars": min_chars,
        "docs_in": len(documents),
        "chunks_out": len(deduped),
        "chunks_before_dedupe": len(all_chunks),
        "chunks_deduped": deduped_count,
        "chunks_dropped_empty": dropped_empty,
        "empty_docs": empty_docs,
        "by_source_id": dict(sorted(by_source.items())),
    }
    return deduped, report
