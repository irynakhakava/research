# Туториал · Фаза 1 · Data pipeline

Цель фазы: превратить статический корпус `[data/corpus/](../../data/corpus/)` в **набор чанков с метаданными**, готовый к индексации (фаза 2).

> Режим проекта: **только статика**. Коннекторов к Confluence/Git нет.  
> «Ингест» = чтение markdown с диска + нормализация + чанкинг + запись артефакта.

Вход фазы 0:


| Артефакт                                 | Зачем                                          |
| ---------------------------------------- | ---------------------------------------------- |
| `data/corpus/**/*.md`                    | тексты                                         |
| `data/corpus/manifest.json`              | id → путь                                      |
| `phase-0-discovery/sources.catalog.yaml` | priority, ACL, owner, team                     |
| `phase-0-discovery/gold-set/`            | позже для проверки, что чанки не «убили» hit’ы |


Выход фазы 1:


| Артефакт                                              | Описание                                     |
| ----------------------------------------------------- | -------------------------------------------- |
| `data/processed/documents.jsonl`                      | нормализованные документы (1 doc = 1 строка) |
| `data/processed/chunks.jsonl`                         | чанки с метаданными (1 chunk = 1 строка)     |
| `data/processed/pipeline_report.json`                 | статистика прогона                           |
| код пайплайна в `src/pipeline/` (или `phase-1-data/`) | воспроизводимая команда сборки               |
| короткий ADR по чанкингу                              | выбранные параметры                          |


---

## Зачем эта фаза

Векторный поиск работает не по «файлам», а по **чанками**. Плохой чанкинг → низкий Recall даже с хорошей моделью эмбеддингов.

На фазе 1 мы:

1. Читаем только нужные источники (`p0` для MVP, опционально `p1`).
2. Нормализуем markdown (frontmatter, заголовки, код).
3. Режем на чанки с overlap и стабильными id.
4. Навешиваем метаданные для фильтров ACL/team (фаза 2).
5. Дедуплицируем и пишем отчёт.

Эмбеддинги и vector DB — **не здесь** (фаза 2).

---

## Архитектура пайплайна (static)

```
sources.catalog.yaml          data/corpus/**/*.md
         │                              │
         ▼                              ▼
   filter priority=p0  ←── join by source_id ──→  load markdown
         │
         ▼
   normalize (strip frontmatter → fields, keep body)
         │
         ▼
   chunk (structure-aware / fixed size)
         │
         ▼
   enrich metadata + content_hash
         │
         ▼
   dedupe → data/processed/{documents,chunks}.jsonl
         │
         ▼
   pipeline_report.json (+ optional smoke vs gold-set doc ids)
```

---

## Шаг 1. Зафиксировать scope ингеста

**Решение MVP:** индексируем документы, чей `source_id` в каталоге имеет `priority: p0`.


| source_id                      | Ожидаемо в корпусе       |
| ------------------------------ | ------------------------ |
| `platform-confluence-runbooks` | runbooks + mesh overview |
| `platform-git-services-readme` | README сервисов          |
| `payments-confluence-ops`      | ops / playbooks          |
| `sre-notion-incident-guides`   | incident guides          |
| `data-git-airflow-runbooks`    | airflow runbooks         |


`p1` (security, architecture, openapi, onboarding, postmortems) — **не в MVP-индекс**, но пайплайн должен уметь прогнать их флагом `--priority p0,p1` для экспериментов.

**Критерий шага:** в коде/конфиге явный allowlist priority; по умолчанию только `p0`.

### Реализация (готово)

- Конфиг: `[phase-1-data/config.yaml](../../phase-1-data/config.yaml)` — `priorities: [p0]`  
- Фильтр: `pipeline/catalog.py` → `filter_sources_by_priority`  
- Запуск: `python phase-1-data/run_documents.py --dry-run`

Почему так: corpus лежит на диске целиком (включая p1), но MVP-индекс не должен «случайно» съесть security/postmortems. Scope задаётся конфигом, а не ручным списком файлов.

---

## Шаг 2. Контракт нормализованного документа

Каждая строка `documents.jsonl`:

```json
{
  "doc_id": "plat-runbook-payments-rollback",
  "source_id": "platform-confluence-runbooks",
  "title": "Runbook: откат релиза payments",
  "path": "data/corpus/platform-confluence-runbooks/plat-runbook-payments-rollback.md",
  "text": "...полный текст без YAML frontmatter...",
  "language": "ru",
  "acl": "team-only",
  "team": "platform",
  "priority": "p0",
  "doc_types": ["runbook", "howto", "troubleshooting"],
  "content_hash": "sha256:...",
  "char_count": 1234,
  "updated_at": "2026-07-22"
}
```

Правила:

- `doc_id` = stem файла / поле `id` из frontmatter (должны совпадать).  
- `text` — markdown body; frontmatter распарсен в поля.  
- Метаданные `acl`, `team`, `priority` — **из catalog по `source_id`**, не выдумывать из текста.  
- `content_hash` = sha256 нормализованного `text` (для дедупа и инкрементальной пересборки).

**Критерий шага:** схема зафиксирована в `phase-1-data/schemas/document.json` (или эквивалент).

### Реализация (готово)


| Файл                                                                | Роль                                     |
| ------------------------------------------------------------------- | ---------------------------------------- |
| `[schemas/document.json](../../phase-1-data/schemas/document.json)` | контракт полей                           |
| `[pipeline/normalize.py](../../phase-1-data/pipeline/normalize.py)` | снять frontmatter, посчитать `sha256`    |
| `[pipeline/load.py](../../phase-1-data/pipeline/load.py)`           | join manifest↔catalog, собрать документы |
| `[run_documents.py](../../phase-1-data/run_documents.py)`           | CLI → `data/processed/documents.jsonl`   |


```bash
python phase-1-data/run_documents.py
# → data/processed/documents.jsonl          (20 docs при p0)
# → data/processed/documents_build_report.json
```

Почему `acl`/`team` из catalog, а не из markdown: страница может врать или не содержать ACL; фильтры доступа в фазе 2 должны опираться на политику источника.

Почему нужен `content_hash`: позже можно не переэмбеддивать неизменённые документы.

Подробнее: `[phase-1-data/README.md](../../phase-1-data/README.md)`.

---

## Шаг 3. Стратегия чанкинга

### Baseline (обязательный для MVP)

**Structure-aware + size cap:**

1. Резать по заголовкам `##` / `###` (секции).
2. Если секция > `max_chars` (рекомендация: **1200–1800** символов ≈ 300–500 токенов) — дорезать по абзацам.
3. Overlap: **150–200** символов с предыдущим чанком (или 1 абзац).
4. Код-блоки (```) не разрывать посередине, если возможно.

### Альтернативы для фазы 4 (не блокируют фазу 1)


| Вариант               | Параметры                                | Зачем сравнивать        |
| --------------------- | ---------------------------------------- | ----------------------- |
| A fixed               | 512 / 1024 tokens, overlap 10–20%        | простой baseline        |
| B structure (default) | по `##`, cap 1500 chars                  | лучше для runbooks      |
| C parent-child        | мелкие чанки + parent section в metadata | для re-ranking / expand |


На фазе 1 реализуем **B** и сохраняем параметры в конфиг, чтобы потом прогнать A/C без переписывания пайплайна.

### Контракт чанка (`chunks.jsonl`)

```json
{
  "chunk_id": "plat-runbook-payments-rollback::0003",
  "doc_id": "plat-runbook-payments-rollback",
  "source_id": "platform-confluence-runbooks",
  "chunk_index": 3,
  "text": "...",
  "heading_path": ["Runbook: откат релиза payments", "Staging: быстрый rollback"],
  "char_count": 980,
  "acl": "team-only",
  "team": "platform",
  "priority": "p0",
  "language": "ru",
  "content_hash": "sha256:..."
}
```

Правила id: `{doc_id}::{chunk_index:04d}` — стабильный при том же тексте и тех же параметрах чанкинга.

**Критерий шага:** ADR-0002 с выбранными `max_chars`, `overlap`, стратегией B.

### Реализация (готово)

| Файл | Роль |
|------|------|
| [`config.yaml`](../../phase-1-data/config.yaml) → `chunking:` | max_chars=1500, overlap=180, min_chars=40 |
| [`pipeline/chunking.py`](../../phase-1-data/pipeline/chunking.py) | strategy B |
| [`schemas/chunk.json`](../../phase-1-data/schemas/chunk.json) | контракт чанка |
| [`adr-0002-chunking.md`](../../phase-1-data/adr-0002-chunking.md) | решение зафиксировано |
| [`run_chunks.py`](../../phase-1-data/run_chunks.py) | CLI → `chunks.jsonl` |

```bash
python phase-1-data/run_chunks.py --from-documents data/processed/documents.jsonl
# → data/processed/chunks.jsonl          (~40 chunks на 20 p0 docs)
# → data/processed/pipeline_report.json
```

**Почему режем по заголовкам, а не fixed-size:** в runbooks ответ обычно лежит в одной секции (`## Staging: rollback`). Fixed window часто разрывает нумерованные шаги.

**Почему не рвём code fences:** команда `kubectl ...` посередине fence бесполезна для retrieval и генерации.

**Почему overlap:** если процедура начинается в конце одного чанка и продолжается в следующем — overlap сохраняет связность на границе.

Подробнее: [`phase-1-data/README.md`](../../phase-1-data/README.md).

---

## Шаг 4. Единый CLI пайплайна

**Зачем:** одна воспроизводимая команда вместо цепочки `run_documents` → `run_chunks`.  
Меньше шансов забыть шаг или прогнать чанкинг на устаревших documents.

### Что делает

`run_pipeline.py` последовательно:

1. load + normalize (шаги 1–2);  
2. chunking B (шаг 3);  
3. quality checks (шаг 5);  
4. запись `documents.jsonl`, `chunks.jsonl`, `pipeline_report.json`.

### Запуск

```bash
python phase-1-data/run_pipeline.py
python phase-1-data/run_pipeline.py --dry-run
python phase-1-data/run_pipeline.py --priority p0,p1
python phase-1-data/run_pipeline.py --max-chars 1200 --overlap 150
```

| Флаг | Default | Смысл |
|------|---------|--------|
| `--priority` | из config (`p0`) | какие source брать |
| `--max-chars` | 1500 | потолок чанка |
| `--overlap` | 180 | overlap символов |
| `--dry-run` | off | только report |
| `--skip-quality-fail` | off | писать файлы даже при quality fail |

**Критерий:** одна команда собирает весь `data/processed/`. — **готово** ([`run_pipeline.py`](../../phase-1-data/run_pipeline.py)).

---

## Шаг 5. Дедупликация и качество данных

**Зачем:** не тащить в фазу 2 (эмбеддинги) битый или неполный набор чанков.

| Проверка | Зачем | Где |
|----------|-------|-----|
| Exact dedupe по `content_hash` | убрать дубликаты текста | `chunking.py` |
| Near-empty drop (`< min_chars`) | шум из одних заголовков | `chunking.py`, счётчик `chunks_dropped_empty` |
| Orphan check | документ без чанков = дыра в индексе | `quality.py` |
| Gold-set p0 smoke | эталонные doc_id из eval доступны | `quality.py` |
| Metadata check | acl/team/heading_path на месте для фильтров | `quality.py` |

При `quality.ok = false` пайплайн **не пишет** jsonl (exit code 1), чтобы не затереть хороший артефакт мусором.

Код: [`pipeline/quality.py`](../../phase-1-data/pipeline/quality.py).  
Отчёт: `data/processed/pipeline_report.json` → блок `quality`.

**Критерий:** report + зелёный smoke. — **готово**.

---

## Шаг 6. Тесты

**Зачем:** зафиксировать инварианты scope/чанкинга/gold-set, чтобы рефакторинг не сломал пайплайн тихо.

| Тест | Что проверяет |
|------|----------------|
| `test_load_joins_catalog` | acl/team из catalog |
| `test_does_not_split_codefence` | fence не рвётся |
| `test_chunk_ids_stable` | стабильные `chunk_id` |
| `test_p0_only_default` | p1 не попадают без флага |
| `test_goldset_p0_docs_present` | p0 relevant docs загружены |
| `test_orphans_and_quality_ok` | quality блок зелёный |
| `test_run_pipeline_cli` | единый CLI dry-run |

```bash
python -m unittest discover -s phase-1-data/tests -v
# ожидаемо: 18 tests OK
```

**Критерий:** suite зелёный. — **готово**.

---

## Шаг 7. DoD фазы 1

**Зачем:** явно сказать «фаза закрыта», иначе бесконечно полируем чанкинг.

Чеклист: [`phase-1-data/CHECKLIST.md`](../../phase-1-data/CHECKLIST.md).

Фаза 1 закрыта, когда:

- [x] CLI собирает `documents.jsonl` + `chunks.jsonl`  
- [x] Default только `p0`  
- [x] Metadata на чанках полная  
- [x] ADR-0002 + config  
- [x] `pipeline_report.json` с quality  
- [x] Тесты зелёные  
- [x] Туториал с реальными командами  

**Не входит в фазу 1:** embeddings, vector DB, BM25, `/search`, LLM.

**Статус: фаза 1 выполнена.** Дальше — фаза 2 (Index & retrieval) поверх `chunks.jsonl`.

---

## Порядок работ (5–7 дней для 1 инженера)


| День | Работа                                         | Результат                      |
| ---- | ---------------------------------------------- | ------------------------------ |
| 1    | Схемы + load/join corpus↔catalog               | `documents` в памяти / dry-run |
| 2    | Normalize + запись `documents.jsonl`           | артефакт документов            |
| 3    | Chunking strategy B + тесты на fence/stability | `chunks.jsonl`                 |
| 4    | Dedupe, report, gold-set smoke                 | `pipeline_report.json`         |
| 5    | ADR-0002, README, полировка CLI                | фаза 1 Done                    |


---

## Риски


| Риск                  | Симптом                         | Митигация                             |
| --------------------- | ------------------------------- | ------------------------------------- |
| Слишком крупные чанки | в контекст LLM не влезает       | cap `max_chars`, эксперимент в фазе 4 |
| Слишком мелкие        | потеря контекста процедуры      | structure-aware, overlap              |
| Metadata забыли       | ACL-фильтры в фазе 2 невозможны | обязательные поля в схеме + тест      |
| Nestability chunk_id  | eval «плывёт»                   | id только от doc+index+config version |


---

## Связь с фазой 2

Фаза 2 читает **только** `data/processed/chunks.jsonl` (и при необходимости documents) и строит dense/hybrid индекс.  
Пересборка индекса = `run_pipeline` → embed/index job.

---

## Что сделать в первую очередь

Фаза 1 закрыта. Для пересборки артефактов:

```bash
python phase-1-data/run_pipeline.py
python -m unittest discover -s phase-1-data/tests -v
```

Дальше — план/туториал **фазы 2** (embeddings + vector/hybrid index).

