# Туториал · Фаза 2 · Index & retrieval

Цель фазы: из `chunks.jsonl` получить **поиск по вопросу** (top-k чанки с фильтрами), пока без LLM.

Режим: только статика. Вход — [`data/processed/chunks.jsonl`](../../data/processed/chunks.jsonl).

| Пункт | Суть | Статус |
|-------|------|--------|
| 1. Embeddings | векторы для каждого чанка | готово |
| 2. Vector + BM25 index | файловый dense + sparse | готово |
| 3. Retrieve + filters | hybrid RRF, ACL/team, CLI | готово |
| 4. `/search` API (сервис) | HTTP later | ожидается / CLI уже есть |
| **5. Offline eval** | Recall@k / MRR на gold-set | готово |

---

## Пункт 1. Embeddings

### Зачем

Чанк — текст. Чтобы сравнивать «похожесть» вопроса и чанка, оба переводятся в **вектор фиксированной длины**. Близкие по смыслу тексты → близкие векторы (cosine).

Без этого шага нельзя сделать dense retrieval (фаза 2.2–2.3).

### Какую модель взяли

**`intfloat/multilingual-e5-small`**

| Критерий | Почему подходит |
|----------|-----------------|
| Языки | ru + en (наш корпус смешанный) |
| Размер | ~120M params — тянется локально без GPU |
| Качество | сильный baseline для retrieval; в фазе 4 сравним с bge-m3 / API |
| Лицензия / доступ | Hugging Face, без облачного API-ключа |

Для e5 обязательны префиксы:

- чанки (passage): `passage: <text>`
- запросы (query, позже): `query: <text>`

Решение зафиксировано в [`phase-2-retrieval/adr-0003-embeddings.md`](../../phase-2-retrieval/adr-0003-embeddings.md).

### Что на выходе

| Файл | Содержание |
|------|------------|
| `data/processed/embeddings.npz` | матрица `(N, dim)` + `chunk_ids` |
| `data/processed/embeddings_meta.json` | model, dim, count, content_hash чанков |

`chunk_id[i]` соответствует строке `vectors[i]` — так фаза 2.2 положит векторы в индекс.

### Как запустить

```bash
# из корня репозитория (рекомендуется локальный .venv)
python3 -m venv .venv
source .venv/bin/activate
pip install -r phase-2-retrieval/requirements.txt

python phase-2-retrieval/run_embed.py --no-reuse
python phase-2-retrieval/run_index.py   # пересобрать индекс после смены модели
```

# dry-run: только посчитать, что будет сделано
python phase-2-retrieval/run_embed.py --dry-run

# тесты (без скачивания модели — hash-backend)
python -m unittest discover -s phase-2-retrieval/tests -v
```

Первый реальный прогон скачает модель с Hugging Face (~hundreds MB).

### Инкремент

Если `content_hash` чанка не изменился и модель та же — вектор переиспользуется из предыдущего `embeddings.npz` (не считаем заново).

### Что не входит в пункт 1

- Запись в Qdrant/pgvector  
- BM25  
- `/search`  
- Eval Recall@k  

Это пункты 2–5.

---

## Пункт 2. Vector + BM25 index

### Зачем

Эмбеддинги сами по себе — просто матрица. Индекс:

1. **Dense** — быстрый cosine по векторам (paraphrases, смысл).  
2. **BM25** — lexical match (точные термины: `kubectl`, `Sev-1`, имена сервисов).  

Вместе (hybrid, пункт 3) обычно лучше, чем любой сигнал отдельно.

### Решение

Файловый индекс (без Qdrant): [`adr-0004-index.md`](../../phase-2-retrieval/adr-0004-index.md).

```
data/processed/index/
  dense.npz           # vectors + chunk_ids
  bm25.json           # postings BM25 Okapi
  chunks_meta.jsonl   # text + acl/team для фильтров
  index_meta.json
```

### Запуск

```bash
# нужен embeddings.npz (хотя бы hash-backend)
python phase-2-retrieval/run_embed.py --backend hash

python phase-2-retrieval/run_index.py
python phase-2-retrieval/run_index.py --dry-run
```

### Что не входит в пункт 2

Hybrid fusion, фильтры ACL, CLI поиска — **пункт 3**.

---

## Пункт 3. Retrieve + filters

### Зачем

Индекс молчит, пока нет запроса. Нужно: вопрос → top-k чанков, с учётом ACL/team.

### Как

1. Dense: эмбеддинг вопроса (`query: …` для e5) → cosine top candidates  
2. BM25: lexical top candidates  
3. **RRF** сливает ранги (`k=60`)  
4. Фильтры `team` / `acl` / `priority` / `source_id` отсекают чанки **до** выдачи  

ADR: [`adr-0005-retrieve.md`](../../phase-2-retrieval/adr-0005-retrieve.md).

### Запуск

```bash
source .venv/bin/activate   # тот же venv, где ставили e5

python phase-2-retrieval/run_search.py "Как откатить payments в staging?"
python phase-2-retrieval/run_search.py "CrashLoop payments" --mode hybrid --top-k 5
python phase-2-retrieval/run_search.py "rollback" --team platform
python phase-2-retrieval/run_search.py "airflow backfill" --mode bm25
```

Ответ — JSON: `hits[]` с `chunk_id`, `score`, `doc_id`, `team`, `text`, ранги dense/bm25.

### Что дальше

Пункт 5 (eval) измеряет качество выдачи на gold-set.

---

## Пункт 5. Offline eval

### Зачем

Без метрик нельзя сказать, что hybrid «лучше» BM25, и нельзя закрыть DoD:

| Критерий | Порог |
|----------|-------|
| Recall@10 | ≥ 0.70 |
| MRR | ≥ 0.50 |

### Как считаем

1. Берём gold-set кейсы `answer` + `priority=p0` (p1 ещё не в индексе MVP).  
2. Для каждого вопроса — search top-k чанков.  
3. Схлопываем в уникальные `doc_id` (порядок первого появления).  
4. **Hit@k / Recall@k**: есть ли хотя бы один `relevant_doc_id` в top-k документов.  
5. **MRR**: среднее `1/rank` первого релевантного документа.

ADR: [`adr-0006-eval.md`](../../phase-2-retrieval/adr-0006-eval.md).

### Запуск

```bash
source .venv/bin/activate

python phase-2-retrieval/run_eval.py
python phase-2-retrieval/run_eval.py --compare dense,bm25
python phase-2-retrieval/run_eval.py --limit 10
python phase-2-retrieval/run_eval.py --fail-under-threshold
```

Отчёт: `data/processed/eval_report.json` (+ сводка в stdout с `misses`).

### Что дальше

Фаза 3 — ответ с цитатами (`/ask`): [03-rag-generation.md](03-rag-generation.md). HTTP `/search` — по желанию в фазе 5.
