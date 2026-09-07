# Туториал · Фаза 3 · RAG generation

Цель фазы: из вопроса получить **ответ с цитатами**, а не только список чанков.

**RAG** = Retrieval-Augmented Generation: сначала поиск (фаза 2), потом текст ответа, опирающийся только на найденные фрагменты.

Вход: индекс `data/processed/index/` + вопрос.  
Выход: JSON с `answer`, `refuse`, `citations[]`.

| Пункт | Суть | Статус |
|-------|------|--------|
| **1. `/ask` + цитаты** | retrieve → generate → path/url | готово |
| **2. Refuse** | секреты, не-доки, низкая уверенность | готово |
| **3. CLI / HTTP** | `run_ask.py`, `POST /ask` | готово |
| **4. Eval** | gold-set refuse + citation contract | готово |

---

## Зачем это отдельно от поиска

`run_search.py` отвечает: «какие куски текста похожи».  
Человек всё ещё сам читает чанки.

`/ask` отвечает фразой и обязан показать **откуда** факт (`citations[]` с `path` и `url`).  
Если фактов нет или вопрос про секреты — система **отказывается**, а не выдумывает.

Пороги DoD (фаза 0):

| Критерий | Порог |
|----------|--------|
| Ответ с корректными цитатами | ≥ 80% (здесь: цитата указывает на эталонный `doc_id`) |
| Refuse-кейсы | ≥ 90% дают `refuse` |
| У каждого ответа есть источники | `citations[].path` / `url` |

---

## Как устроен `/ask`

1. **Retrieve** — тот же hybrid RRF, что в фазе 2 (фильтры `team` / `acl` **до** генерации).  
2. **Refuse-гейт**  
   - вопрос про пароль / ключ / зарплату → `secret`  
   - отпуск, личное → `out_of_scope`  
   - пустая выдача или низкий dense cosine → `low_confidence` / `empty_retrieval`  
   Политика NFR: **refuse_with_nearest_links** — короткий отказ + до 3 ссылок без «фактов».  
3. **Generate** — по умолчанию **extractive**: склеить текст чанков и поставить маркеры `[1]`, `[2]`. Ничего из «головы модели».  
4. **Citations** — `path` из `documents.jsonl`, `url` = `catalog.location#doc_id`.

ADR: [`adr-0007-generation.md`](../../phase-3-generation/adr-0007-generation.md).

LLM не обязателен. Опционально `backend: openai` (ключ `OPENAI_API_KEY`) — сравнение моделей в фазе 4.

---

## Запуск

Нужны индекс и `.venv` фазы 2 (модель e5 для hybrid).

```bash
source .venv/bin/activate

python phase-3-generation/run_ask.py "Как откатить payments в staging?"
python phase-3-generation/run_ask.py "Какой пароль от прод-БД payments?"
python phase-3-generation/run_ask.py "Когда Иванов выйдет из отпуска?"

python phase-3-generation/run_ask_eval.py --fail-under-threshold
```

Ответ CLI — JSON. Поля: `answer`, `refuse`, `refuse_reason`, `citations[]`, `confidence`.

### HTTP (тонкий сервер)

Полный сервис — фаза 5. Здесь stdlib, тот же JSON:

```bash
python phase-3-generation/run_server.py
curl -s http://127.0.0.1:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Как откатить payments в staging?"}'
```

### Тесты (без скачивания модели)

```bash
python -m unittest discover -s phase-3-generation/tests -v
```

---

## Что не входит

- Диалог с памятью  
- LLM-as-judge на 50 сэмплах (человеческая оценка / фаза 4)  
- Прод-деплой, auth, rate limit  

---

## Что дальше

Фаза 4 — эксперименты (эмбеддинги / LLM).  
Фаза 5 — сервис: `/search` + `/ask`, ops.
