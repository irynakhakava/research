# ADR-0006 · Offline retrieval eval (фаза 2, пункт 5)

- **Статус:** accepted  
- **Дата:** 2026-09-07  
- **Связь:** [туториал · пункт 5](../docs/tutorials/02-index-retrieval.md#пункт-5-offline-eval)

## Решение

| Параметр | Значение |
|----------|----------|
| Источник | `phase-0-discovery/gold-set/dataset.jsonl` |
| Кейсы | `expected_behavior=answer`, по умолчанию `source_priority=p0` |
| Гранулярность | **документ**: чанки → уникальные `doc_id` в порядке первого hit |
| Метрики | Recall@k (binary hit), MRR (1/rank первого релевантного) |
| k | 1, 5, 10 (DoD смотрит Recall@10 и MRR) |
| Пороги DoD | Recall@10 ≥ 0.70, MRR ≥ 0.50 |
| Отчёт | `data/processed/eval_report.json` |

## Почему document-level

Gold-set размечен `relevant_doc_ids` / `primary_doc_id`, не chunk_id. Чанкинг может меняться — метрики не должны «плыть» из‑за сдвига границ.

## Почему только p0 по умолчанию

MVP-пайплайн индексирует только p0. p1-кейсы дали бы системный miss не из‑за retrieval.

## Refuse

Кейсы `refuse` не входят в Recall/MRR (нет эталонных doc). Их проверяет фаза 3 (генерация).
