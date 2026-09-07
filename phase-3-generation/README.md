# Phase 3 · RAG generation

Вопрос → retrieve (фаза 2) → отказ или ответ **только из чанков** + `citations[]`.

| Пункт | Статус |
|-------|--------|
| 1. `/ask` + цитаты | **готово** |
| 2. Refuse (секреты / не-доки / низкая уверенность) | **готово** |
| 3. CLI + минимальный HTTP | **готово** |
| 4. Eval на gold-set | **готово** |

## Команды

```bash
source .venv/bin/activate

python phase-3-generation/run_ask.py "Как откатить payments в staging?"
python phase-3-generation/run_ask.py "Какой пароль от прод-БД payments?"

python phase-3-generation/run_ask_eval.py --fail-under-threshold

# опционально: HTTP
python phase-3-generation/run_server.py
# POST http://127.0.0.1:8080/ask  {"question":"..."}
```

LLM не обязателен. По умолчанию `generation.backend: extractive`.  
Для Chat Completions: `--backend openai` и `OPENAI_API_KEY`.

## Контракт ответа

`refuse`, `answer`, `citations[]` (`path`, `url`, `chunk_id`, `doc_id`, `quote`).

ADR: [adr-0007-generation.md](adr-0007-generation.md)

## Тесты

```bash
python -m unittest discover -s phase-3-generation/tests -v
```
