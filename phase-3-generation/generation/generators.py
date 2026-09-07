"""Генераторы ответа: extractive (без сети) и опциональный OpenAI-compatible LLM."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Sequence

from retrieval.retrieve import SearchHit

from .citations import Citation

_HEADING_RE = re.compile(r"^#{1,6}\s+")


def _clean_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    line = _HEADING_RE.sub("", line)
    return line


def _excerpt_chunk(text: str, max_chars: int = 420) -> str:
    """Короткий фрагмент из чанка: списки, команды, первые абзацы."""
    keep: list[str] = []
    in_fence = False
    fence_buf: list[str] = []
    for raw in (text or "").splitlines():
        if raw.strip().startswith("```"):
            if in_fence:
                fence_buf.append(raw.strip())
                keep.append("\n".join(fence_buf))
                fence_buf = []
                in_fence = False
            else:
                in_fence = True
                fence_buf = [raw.strip()]
            continue
        if in_fence:
            fence_buf.append(raw.rstrip())
            continue
        line = _clean_line(raw)
        if not line or line.startswith("---"):
            continue
        keep.append(line)
        if sum(len(x) for x in keep) >= max_chars:
            break
    if in_fence and fence_buf:
        keep.append("\n".join(fence_buf[:8]))
    joined = "\n".join(keep).strip()
    if len(joined) > max_chars:
        return joined[:max_chars].rstrip() + "…"
    return joined


def generate_extractive(
    question: str,
    hits: Sequence[SearchHit],
    citations: Sequence[Citation],
    *,
    max_chunks: int = 4,
) -> str:
    """Ответ только из текста чанков + маркеры [n]. Ничего не выдумывает."""
    del question  # вопрос уже отобрал чанки; extractive не перефразирует «из головы»
    used = list(zip(hits[:max_chunks], citations[:max_chunks]))
    if not used:
        return "В контексте нет фрагментов."

    blocks: list[str] = []
    for hit, cit in used:
        heading = " / ".join(hit.heading_path) if hit.heading_path else hit.doc_id
        excerpt = _excerpt_chunk(hit.text)
        if not excerpt:
            continue
        blocks.append(f"**{heading}** [{cit.index}]\n{excerpt}")

    if not blocks:
        return "В найденных фрагментах нет читаемого текста."

    return (
        "По внутренней документации (только цитаты из найденных фрагментов):\n\n"
        + "\n\n".join(blocks)
    )


def _context_block(hits: Sequence[SearchHit], citations: Sequence[Citation]) -> str:
    parts: list[str] = []
    for hit, cit in zip(hits, citations):
        heading = " / ".join(hit.heading_path) if hit.heading_path else hit.doc_id
        parts.append(
            f"[{cit.index}] doc_id={hit.doc_id} path={cit.path} ({heading})\n{hit.text}"
        )
    return "\n\n".join(parts)


SYSTEM_PROMPT = """Ты ассистент по внутренней документации NordLedger.
Отвечай ТОЛЬКО фактами из блока CONTEXT. Если фактов нет — скажи, что не можешь ответить.
Не выдумывай шаги, URL, пароли, имена людей.
После утверждений ставь маркеры источников [1], [2] как в CONTEXT.
Секреты, пароли, ключи, зарплаты не раскрывай — откажись.
Отвечай на языке вопроса (обычно русский). Кратко, по делу."""


def generate_openai(
    question: str,
    hits: Sequence[SearchHit],
    citations: Sequence[Citation],
    *,
    model: str,
    base_url: str,
    api_key: str,
    timeout_s: float = 45.0,
) -> str:
    body = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"QUESTION:\n{question}\n\nCONTEXT:\n{_context_block(hits, citations)}"
                ),
            },
        ],
    }
    url = base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM returned no choices")
    return str(choices[0].get("message", {}).get("content") or "").strip()


def resolve_api_key() -> str:
    return (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("NORDLEDGER_LLM_KEY")
        or ""
    )
