# ADR-0004 · Формат индекса dense + BM25 (фаза 2, пункт 2)

- **Статус:** accepted  
- **Дата:** 2026-09-04  
- **Связь:** [туториал · пункт 2](../docs/tutorials/02-index-retrieval.md#пункт-2-vector--bm25-index)

## Контекст

Нужно хранить dense-векторы и sparse BM25 для ~40 чанков. Проект static-only, без Docker/Qdrant в MVP.

## Решение

Файловый гибридный индекс в `data/processed/index/`:

| Файл | Роль |
|------|------|
| `dense.npz` | vectors + chunk_ids |
| `bm25.json` | postings / df / doc_len (BM25 Okapi) |
| `chunks_meta.jsonl` | текст + acl/team для фильтров |
| `index_meta.json` | model, dim, n_chunks |

Dense scoring: cosine через dot product (векторы нормализованы).  
Sparse: свой BM25 Okapi (`k1=1.5`, `b=0.75`), без внешних пакетов.

## Почему не Qdrant/OpenSearch сейчас

| Вариант | Почему отложили |
|---------|-----------------|
| Qdrant | лишний сервис для 40 чанков |
| OpenSearch | тяжело для demo |
| Только dense | хуже на точных терминах (kubectl, Sev-1) |
| Только BM25 | хуже на paraphrases |

В фазе 4/5 можно заменить storage на Qdrant, контракт `chunk_id` + metadata сохранится.

## Последствия

- Сборка: `python phase-2-retrieval/run_index.py`  
- После смены embeddings — пересобрать индекс  
- Hybrid fusion и ACL-фильтры — пункт 3
