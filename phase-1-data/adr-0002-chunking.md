# ADR-0002 · Стратегия чанкинга (фаза 1)

- **Статус:** accepted  
- **Дата:** 2026-07-22  
- **Связь:** [туториал · шаг 3](../docs/tutorials/01-data-pipeline.md#шаг-3-стратегия-чанкинга)

## Контекст

Нужно резать нормализованные markdown-документы на чанки для будущего векторного индекса. Корпус — runbooks/how-to со структурой заголовков и code fences.

## Решение

**Strategy B — structure-aware + size cap:**

| Параметр | Значение |
|----------|----------|
| `strategy` | `structure_b` |
| `max_chars` | `1500` |
| `overlap` | `180` |
| `min_chars` | `40` |

Правила:

1. Секции по заголовкам `#` / `##` / `###`.  
2. Секция длиннее `max_chars` → дробление по абзацам с `overlap`.  
3. Fenced code blocks (` ``` `) не разрываются посередине (если блок целиком > max_chars — жёсткий split).  
4. `chunk_id = {doc_id}::{chunk_index:04d}`.  
5. Metadata (`acl`, `team`, `priority`) копируется из документа.

## Почему не A/C сейчас

- **A (fixed tokens)** — проще, но хуже для процедурных runbooks (режет шаги mid-list). Оставим для A/B в фазе 4.  
- **C (parent-child)** — полезно для expand, усложняет индекс; отложено.

## Последствия

- Пересборка чанков: `python phase-1-data/run_chunks.py`  
- Смена `max_chars`/`overlap` меняет `chunk_id` индексы → нужна полная переиндексация в фазе 2.  
- Параметры живут в `phase-1-data/config.yaml` → `chunking:`.
