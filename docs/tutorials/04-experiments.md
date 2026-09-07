# Туториал · Фаза 4 · Experiments

Цель: понять, **какой вариант поиска и `/ask` лучше на нашем gold-set**, не строя сервис.

Вход: индекс фазы 2 + gold-set фазы 0.  
Выход: таблица метрик и «победитель» сетки.

| Пункт | Суть | Статус |
|-------|------|--------|
| 1. Сетка retrieval | hybrid vs dense vs BM25 | готово |
| 2. Сетка `/ask` | порог refuse + top_k | готово |
| 3. Отчёт | `report.md` + `report.json` | готово |

---

## Зачем

Один прогон `run_eval` / `run_ask_eval` фиксирует *текущие* цифры.  
Фаза 4 крутит **несколько настроек подряд** и пишет сравнение.

На маленьком корпусе (40 чанков) Recall@10 часто 1.0 у всех режимов — смотри **MRR** и **Recall@1**.  
Для `/ask` важно не только `refuse_rate` на секретах, но и чтобы обычные вопросы **не** отказывались из‑за слишком высокого порога (`answered_rate`).

---

## Что сравниваем (и чего нет)

| Сравниваем | Не в baseline |
|------------|----------------|
| `hybrid` / `dense` / `bm25` | новая модель эмбеддингов (`bge-m3`) — сначала пересобери индекс |
| `min_dense_score` 0.20 / 0.28 / 0.40 | LLM-judge на 50 сэмплах |
| `top_k` 3 и 5 | полный cartesian всех осей |

LLM (`backend: openai`) включается только если в конфиге `include_openai: true` и есть `OPENAI_API_KEY`.

ADR: [`adr-0008-experiments.md`](../../phase-4-experiments/adr-0008-experiments.md).

---

## Запуск

Нужен `.venv` и собранный индекс (как для `run_search.py`).

```bash
source .venv/bin/activate

python phase-4-experiments/run_experiments.py
```

Полный прогон: 3 режима поиска + 6 вариантов `/ask` (3 порога × 2 top_k) на 22+3 кейсах. Обычно 1–3 минуты после загрузки e5.

Узкие прогоны:

```bash
python phase-4-experiments/run_experiments.py --only retrieval
python phase-4-experiments/run_experiments.py --only ask --answer-limit 8
```

Отчёты:

- `data/processed/experiments/report.md`
- `data/processed/experiments/report.json`

Сетка в `phase-4-experiments/config.yaml` → блок `experiments:`.

---

## Как читать победителя

- **retrieval** — выше Recall@10, при равенстве выше MRR.  
- **`/ask`** — сначала пороги DoD (refuse ≥ 0.90, цитаты, grounded среди отвеченных ≥ 0.80), потом больше отвеченных how-to (не ложный refuse).

Смена модели эмбеддингов (фаза 4 «вручную»):

```bash
# поменять model_name в phase-2-retrieval/config.yaml
python phase-2-retrieval/run_embed.py --no-reuse
python phase-2-retrieval/run_index.py
python phase-4-experiments/run_experiments.py --only retrieval
```

---

## Что дальше

Фаза 5 — сервис: [05-service-ops.md](05-service-ops.md).
