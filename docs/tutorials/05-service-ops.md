# Туториал · Фаза 5 · Service & ops

Цель: из CLI сделать **один сервис**, который можно дергать по HTTP, и зафиксировать ops: пересборка индекса + CI.

| Пункт | Суть | Статус |
|-------|------|--------|
| **1. HTTP API** | `/health`, `/search`, `/ask` | готово |
| **2. Логи** | `trace_id`, чанки, refuse, latency | готово |
| **3. Rebuild** | одна команда corpus → index | готово |
| **4. CI** | unittest + dry-run, без e5 | готово |

---

## Зачем

Фазы 2–3 уже умеют искать и отвечать из терминала. Для демо «как микросервис» нужны:

- стабильные URL (`POST /search`, `POST /ask`)  
- `trace_id` в ответе и в логе (NFR)  
- команда «перечитай markdown и пересобери индекс»  
- зелёный CI на каждый push  

Auth, k8s, APM — не входят в этот MVP.

---

## API

Тело запроса — JSON. Поле вопроса: `question` (или `query`).

| Метод | Путь | Ответ |
|-------|------|--------|
| GET | `/health` | `{ok, endpoints}` |
| POST | `/search` | `hits[]` как у `run_search.py` + `trace_id` |
| POST | `/ask` | `answer`, `refuse`, `citations[]` + `trace_id` |

Опционально в теле: `mode`, `top_k`, `team`, `acl`, `priority`, `source_id`.  
Заголовок `X-Trace-Id` — свой id; иначе сервер выдаст UUID.

Лог (stderr, одна JSON-строка): `trace_id`, `retrieved_chunk_ids`, `filters`, `embedding_model`, `llm_model`, `refuse`, `latency_ms`. Текст вопроса в лог не пишем (секреты).

ADR: [`adr-0009-service.md`](../../phase-5-service/adr-0009-service.md).

---

## Запуск

Нужен индекс фазы 2 и `.venv` с e5.

```bash
source .venv/bin/activate
python phase-5-service/run_server.py
```

В другом терминале:

```bash
curl -s http://127.0.0.1:8080/health

curl -s http://127.0.0.1:8080/search \
  -H 'Content-Type: application/json' \
  -d '{"question":"Как откатить payments в staging?"}'

curl -s http://127.0.0.1:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Какой пароль от прод-БД payments?"}'
```

Остановка сервера: **Ctrl+C**.  
`deactivate` только выключает `.venv`, сервер сам не гасит.

---

## Пересборка после правки `data/corpus`

```bash
python phase-5-service/run_rebuild.py --dry-run
python phase-5-service/run_rebuild.py
```

Шаги: `run_pipeline.py` → `run_embed.py` → `run_index.py`.  
Потом перезапустить `run_server.py` (индекс читается при старте).

---

## CI

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml): gold-set, корпус, unit-тесты фаз 1–5, `run_rebuild.py --dry-run`.

Полный `run_eval.py` на e5 в Actions не гоняем (тяжёлый torch). Локально:

```bash
python phase-2-retrieval/run_eval.py --limit 10 --fail-under-threshold
python phase-3-generation/run_ask_eval.py --fail-under-threshold
```

---

## Что закрыто из DoD

| # | Критерий | Как |
|---|---------|-----|
| 5 | citations path/url | `/ask` |
| 7 | ACL | фильтры до выдачи + тесты |
| 9 | пересборка одной командой | `run_rebuild.py` |
| 10 | eval/smoke в CI | unittest + dry-run |

Не закрыто на staging-нагрузке: p95 latency (NFR-1/2), human-judge на 50 сэмплах.

---

## Что дальше (вне фаз)

- IdP / ACL claims  
- Docker / деплой  
- OpenTelemetry  
- вторая модель эмбеддингов (фаза 4, вручную)
