# Чеклист фазы 0 · Discovery

Отмечайте по мере выполнения. Детали шагов — в [туториале](../docs/tutorials/00-discovery.md).

Режим: **только статические данные** (`data/corpus/`).

## Артефакты

- [x] `sources.catalog.yaml` — статическая модель источников NordLedger
- [x] `data/corpus/` — markdown-документы + `manifest.json`
- [x] `query-taxonomy.md` — ≥3 типов с примерами, фокус how-to
- [x] `nfr.md` — latency / ACL / freshness под static mode (draft-значения ок для демо)
- [x] `definition-of-done.md` — черновик порогов есть
- [x] `adr-0001-mvp-scope.md` — статус `accepted` (static-only)
- [x] `gold-set/dataset.jsonl` — 36 кейсов (≥30)
- [x] `validate_gold_set.py` + `verify_corpus.py` → OK; покрытие корпуса 31/31

## Готово к фазе 1

- [x] Gold-set ≥30
- [x] Таксономия и NFR достаточны для static corpus
- [x] Фаза 1 читает только `data/corpus`, без коннекторов

**Фаза 0 закрыта.** Дальше: [туториал фазы 1](../docs/tutorials/01-data-pipeline.md).
