# ADR-0009 · HTTP service & rebuild (фаза 5)

- **Статус:** accepted  
- **Дата:** 2026-09-07  
- **Связь:** [туториал](../docs/tutorials/05-service-ops.md)

## Решение

| Параметр | Значение |
|----------|----------|
| Транспорт | stdlib `ThreadingHTTPServer` (без FastAPI) |
| Эндпоинты | `GET /health`, `POST /search`, `POST /ask` |
| Контракт | тот же JSON, что CLI фаз 2–3, плюс `trace_id` |
| Логи | одна JSON-строка на запрос: trace_id, chunks, filters, models, refuse, latency_ms |
| Пересборка | `run_rebuild.py`: pipeline → embed → index |
| CI | unit-тесты + validate gold/corpus + rebuild `--dry-run` (без torch/e5) |

## Почему не FastAPI / Docker в MVP

Меньше зависимостей, тот же Python что и CLI. Деплой в k8s / auth / OpenTelemetry — после демо, если понадобится.

## Почему eval e5 не в GitHub Actions

Модель и torch тяжёлые. DoD #10 закрываем командами, которые зелёные без GPU: unittest + dry-run rebuild. Полноценный `run_eval.py` остаётся локально в `.venv`.
