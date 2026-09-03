# Чеклист / DoD · Фаза 1 Data pipeline

Режим: static corpus only (`data/corpus`).

## Шаги

| Шаг | Описание | Статус |
|-----|----------|--------|
| 1. Scope | `priorities: [p0]` в config | done |
| 2. Documents | `documents.jsonl` + schema | done |
| 3. Chunking B | `chunks.jsonl` + ADR-0002 | done |
| 4. Unified CLI | `run_pipeline.py` одной командой | done |
| 5. Quality | orphans, gold smoke, dedupe/empty в report | done |
| 6. Tests | unittest discover, 18 tests | done |
| 7. DoD | этот чеклист закрыт | done |

## Definition of Done

- [x] CLI собирает `documents.jsonl` + `chunks.jsonl` из static corpus  
- [x] По умолчанию только `priority: p0`  
- [x] Чанки несут `doc_id`, `source_id`, `acl`, `team`, `priority`, `heading_path`  
- [x] Параметры чанкинга в `config.yaml` + `adr-0002-chunking.md`  
- [x] `pipeline_report.json` после прогона (с блоком `quality`)  
- [x] Юнит/smoke тесты зелёные  
- [x] Туториал содержит реальные команды запуска  

**Не входит:** embeddings, vector DB, `/search`, LLM.

## Команда закрытия

```bash
python phase-1-data/run_pipeline.py
python -m unittest discover -s phase-1-data/tests -v
```

**Фаза 1 закрыта.** Дальше — фаза 2 (Index & retrieval).
