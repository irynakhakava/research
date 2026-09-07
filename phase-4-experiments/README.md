# Phase 4 · Experiments

Сравнения на **том же gold-set** и **том же индексе**. Нового сервиса нет.

| Ось | Статус |
|-----|--------|
| Режимы retrieval | hybrid / dense / bm25 |
| Порог `/ask` (`min_dense_score`) | сетка |
| `top_k` контекста | сетка |
| Вторая модель эмбеддингов / LLM | опционально, не baseline |

## Команда

```bash
source .venv/bin/activate

python phase-4-experiments/run_experiments.py
python phase-4-experiments/run_experiments.py --only retrieval
python phase-4-experiments/run_experiments.py --only ask --answer-limit 8
```

Отчёты: `data/processed/experiments/report.md` и `report.json`.

ADR: [adr-0008-experiments.md](adr-0008-experiments.md)

## Тесты

```bash
python -m unittest discover -s phase-4-experiments/tests -v
```
