# Phase 4 · experiment report

Index: `/Users/irina/Documents/Projects/research/data/processed/index`
Gold-set: `/Users/irina/Documents/Projects/research/phase-0-discovery/gold-set/dataset.jsonl`

## Retrieval (answer / p0)

| mode | Recall@1 | Recall@5 | Recall@10 | MRR | n |
|------|----------|----------|-----------|-----|---|
| hybrid | 0.864 | 1.000 | 1.000 | 0.924 | 22 |
| dense | 0.955 | 1.000 | 1.000 | 0.970 | 22 |
| bm25 | 0.818 | 1.000 | 1.000 | 0.867 | 22 |

## /ask

| backend | min_dense | top_k | refuse | answered | grounded (answered) | citations |
|---------|-----------|-------|--------|----------|---------------------|-----------|
| extractive | 0.200 | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| extractive | 0.200 | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| extractive | 0.280 | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| extractive | 0.280 | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| extractive | 0.400 | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| extractive | 0.400 | 5 | 1.000 | 1.000 | 1.000 | 1.000 |

## Winners

- retrieval: **dense** (Recall@10=1.000, MRR=0.970)
- /ask: **extractive** min_dense_score=0.2 top_k=3

На маленьком p0-корпусе dense часто чуть лучше hybrid по MRR — это не повод выкидывать BM25 на большем наборе.

