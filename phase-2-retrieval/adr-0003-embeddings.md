# ADR-0003 · Модель эмбеддингов (фаза 2, пункт 1)

- **Статус:** accepted  
- **Дата:** 2026-09-04  
- **Связь:** [туториал · пункт 1](../docs/tutorials/02-index-retrieval.md#пункт-1-embeddings)

## Контекст

Нужны dense-векторы для ~40 чанков (p0) на русском и английском. Проект static-only, без облачных API по умолчанию.

## Решение

| Поле | Значение |
|------|----------|
| Модель | `intfloat/multilingual-e5-small` |
| Backend | `sentence-transformers` |
| Dim | 384 |
| Metric (позже) | cosine |
| Prefix passage | `passage: ` |
| Prefix query | `query: ` (фаза 2.3+) |

Альтернатива для тестов без сети: backend `hash` (детерминированный псевдо-вектор) — **не для качества**, только для CI/unit.

## Почему не другие варианты сейчас

| Вариант | Почему не baseline |
|---------|-------------------|
| OpenAI `text-embedding-3` | нужен API key / сеть на каждый rebuild |
| `bge-m3` | тяжелее; оставим для фазы 4 |
| Только BM25 | не закрывает dense retrieval |
| `all-MiniLM-L6-v2` | слабее на русском |

## Последствия

- `pip install -r phase-2-retrieval/requirements.txt`  
- Первый прогон качает веса модели  
- Смена модели → полная пересборка embeddings + (позже) индекса  
- Параметры в `phase-2-retrieval/config.yaml`
