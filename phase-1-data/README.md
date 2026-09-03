# Phase 1 · Data pipeline

Статический ингест: `data/corpus` → нормализованные документы → чанки.  
Коннекторов к Confluence/Git нет.

| Шаг | Суть | Статус |
|-----|------|--------|
| 1 | Scope `p0` | done |
| 2 | `documents.jsonl` | done |
| 3 | Chunking B → `chunks.jsonl` | done |
| 4 | Единый CLI `run_pipeline.py` | done |
| 5 | Quality (orphans, gold smoke, dedupe) | done |
| 6 | Тесты | done |
| 7 | DoD | done → [CHECKLIST.md](CHECKLIST.md) |

---

## Главная команда (шаг 4)

```bash
python phase-1-data/run_pipeline.py
```

Одной командой:

1. читает corpus + catalog (только `p0`);  
2. пишет `data/processed/documents.jsonl`;  
3. режет чанки → `data/processed/chunks.jsonl`;  
4. гоняет quality-проверки;  
5. пишет `data/processed/pipeline_report.json`.

Полезные флаги:

```bash
python phase-1-data/run_pipeline.py --dry-run
python phase-1-data/run_pipeline.py --priority p0,p1
python phase-1-data/run_pipeline.py --max-chars 1200 --overlap 150
```

Узкие CLI (если нужны по отдельности):

```bash
python phase-1-data/run_documents.py   # только шаги 1–2
python phase-1-data/run_chunks.py --from-documents data/processed/documents.jsonl
```

Тесты (шаг 6):

```bash
python -m unittest discover -s phase-1-data/tests -v
```

---

## Описания шагов 4–7

### Шаг 4 — единый пайплайн

**Зачем:** не держать в голове два скрипта и порядок запуска.  
**Что:** `run_pipeline.py` = load → documents → chunks → quality → write.  
**Критерий:** одна команда воспроизводимо собирает `data/processed/`.

### Шаг 5 — качество данных

**Зачем:** поймать дыры до фазы 2 (эмбеддинги дорого переигрывать).

| Проверка | Смысл |
|----------|--------|
| Exact dedupe | одинаковый `content_hash` → оставляем первый chunk |
| Near-empty drop | чанки `< min_chars` (40) отбрасываются, счётчик в report |
| Orphan check | каждый document дал ≥1 chunk |
| Gold-set smoke | все p0 `relevant_doc_ids` из gold-set есть в documents |
| Metadata | у чанка есть acl/team/priority/heading_path |

При fail quality выходные файлы **не пишутся** (кроме `--skip-quality-fail`).

### Шаг 6 — тесты

Покрывают join catalog, p0-only, fence/stability чанкинга, gold-set coverage, CLI dry-run.  
Ожидаемо: **18** тестов OK.

### Шаг 7 — DoD

Чеклист закрытия: [CHECKLIST.md](CHECKLIST.md).  
Фаза 1 не включает embeddings / vector DB / API поиска.

---

## Выходы

```
data/processed/
  documents.jsonl         # 20 docs (p0)
  chunks.jsonl            # ~40 chunks
  pipeline_report.json    # config + chunking stats + quality
```

Параметры чанкинга: `config.yaml` → `chunking:` и [adr-0002-chunking.md](adr-0002-chunking.md).

---

## Структура

```
phase-1-data/
  run_pipeline.py          # шаг 4 (главный вход)
  run_documents.py / run_chunks.py
  pipeline/
    catalog.py, normalize.py, load.py
    chunking.py            # шаг 3
    quality.py             # шаг 5
  tests/                   # шаг 6
  CHECKLIST.md             # шаг 7
```

Туториал: [docs/tutorials/01-data-pipeline.md](../docs/tutorials/01-data-pipeline.md).
