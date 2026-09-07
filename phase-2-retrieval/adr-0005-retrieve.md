# ADR-0005 · Hybrid retrieve (фаза 2, пункт 3)

- **Статус:** accepted  
- **Дата:** 2026-09-04  
- **Связь:** [туториал · пункт 3](../docs/tutorials/02-index-retrieval.md#пункт-3-retrieve--filters)

## Решение

| Параметр | Значение |
|----------|----------|
| Fusion | Reciprocal Rank Fusion (RRF), `k=60` |
| Modes | `hybrid` (default), `dense`, `bm25` |
| Filters | `team`, `acl`, `priority`, `source_id` — **до** выдачи |
| Query embed | тот же backend/модель, что индекс (`query: ` prefix для e5) |

## Почему RRF

Не нужно нормализовать разнородные шкалы dense cosine и BM25. Ранги стабильнее на маленьком корпусе.

## ACL

Фильтр отсекает чанки до формирования ответа. Пользователь с `team=data` не видит `platform` даже в mid-ranking.
