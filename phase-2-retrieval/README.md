# Phase 2 · Index & retrieval

| Пункт | Статус |
|-------|--------|
| 1. Embeddings | готово |
| 2. Vector + BM25 index | готово |
| 3. Retrieve + filters | готово |
| 4. HTTP `/search` | опционально (CLI есть) |
| 5. Offline eval | **готово** |

## Команды

```bash
source .venv/bin/activate

python phase-2-retrieval/run_embed.py
python phase-2-retrieval/run_index.py
python phase-2-retrieval/run_search.py "Как откатить payments в staging?"
python phase-2-retrieval/run_search.py "rollback" --team platform --top-k 3
python phase-2-retrieval/run_eval.py
python phase-2-retrieval/run_eval.py --compare dense,bm25
```

## Retrieve (пункт 3)

- Modes: `hybrid` (RRF) / `dense` / `bm25`  
- Filters: `--team` `--acl` `--priority` `--source-id`  
- ADR: [adr-0005-retrieve.md](adr-0005-retrieve.md)

## Eval (пункт 5)

- Gold-set `answer` + `p0` → Recall@k / MRR (document-level)  
- Пороги DoD: Recall@10 ≥ 0.70, MRR ≥ 0.50  
- ADR: [adr-0006-eval.md](adr-0006-eval.md)  
- Отчёт: `data/processed/eval_report.json`

## Тесты

```bash
python -m unittest discover -s phase-2-retrieval/tests -v
```
