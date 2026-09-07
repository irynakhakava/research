# Phase 5 · Service & ops

Один HTTP-сервис поверх фаз 2–3: `/search` и `/ask`.  
Плюс одна команда пересборки индекса и CI.

| Пункт | Статус |
|-------|--------|
| `GET /health` | готово |
| `POST /search` | готово |
| `POST /ask` | готово |
| JSON-логи (trace_id) | готово |
| `run_rebuild.py` | готово |
| GitHub Actions | готово |

## Запуск сервера

```bash
source .venv/bin/activate
python phase-5-service/run_server.py
```

```bash
curl -s http://127.0.0.1:8080/health

curl -s http://127.0.0.1:8080/search \
  -H 'Content-Type: application/json' \
  -d '{"question":"Как откатить payments в staging?","top_k":3}'

curl -s http://127.0.0.1:8080/ask \
  -H 'Content-Type: application/json' \
  -H 'X-Trace-Id: demo-1' \
  -d '{"question":"Как откатить payments в staging?"}'
```

Фильтры в теле: `team`, `acl`, `priority`, `source_id`, `mode`.

Остановка: `Ctrl+C`.

## Пересборка индекса

```bash
python phase-5-service/run_rebuild.py --dry-run
python phase-5-service/run_rebuild.py
```

## Тесты

```bash
python -m unittest discover -s phase-5-service/tests -v
```

ADR: [adr-0009-service.md](adr-0009-service.md)
