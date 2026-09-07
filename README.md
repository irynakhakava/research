# Поиск по документации команд (RAG)

Микросервис векторного поиска: вопрос пользователя → релевантные фрагменты документации → ответ LLM с цитатами.

## Режим данных: только статика

Проект **не подключается** к реальному Confluence/Notion/Git.  
Единственный корпус для индексации и поиска — markdown в [`data/corpus/`](data/corpus/).  
Каталог источников и URL в нём — метаданные демо-орг. NordLedger (описывают «как будто» источники), а не живые коннекторы.

| Артефакт | Роль |
|----------|------|
| `data/corpus/**/*.md` | тексты, по которым ищем ответы |
| `phase-0-discovery/sources.catalog.yaml` | описание корпусов, ACL, приоритеты |
| `phase-0-discovery/gold-set/dataset.jsonl` | вопросы и эталонные doc id для eval |

## Как идти по проекту

Разработка разбита на фазы. Каждая фаза сопровождается туториалом: что делаем, зачем, какие артефакты получаем.

| Фаза | Туториал | Статус |
|------|----------|--------|
| 0. Discovery | [docs/tutorials/00-discovery.md](docs/tutorials/00-discovery.md) | выполнена |
| 1. Data pipeline | [docs/tutorials/01-data-pipeline.md](docs/tutorials/01-data-pipeline.md) | выполнена |
| 2. Index & retrieval | [docs/tutorials/02-index-retrieval.md](docs/tutorials/02-index-retrieval.md) | пункты 1–3, 5 (4 HTTP optional) |
| 3. RAG generation | [docs/tutorials/03-rag-generation.md](docs/tutorials/03-rag-generation.md) | `/ask` + цитаты |
| 4. Experiments | — | ожидается |
| 5. Service & ops | — | ожидается |

## Быстрый старт (фаза 0)

```bash
# 1. Туториал
open docs/tutorials/00-discovery.md

# 2. Проверить gold-set и покрытие корпуса
python phase-0-discovery/gold-set/validate_gold_set.py
python data/corpus/verify_corpus.py
```

## Структура

```
docs/tutorials/          # пошаговые туториалы
phase-0-discovery/       # артефакты Discovery
  sources.catalog.yaml   # каталог источников документации
  nfr.md                 # нефункциональные требования
  query-taxonomy.md      # типы пользовательских запросов
  definition-of-done.md  # критерии готовности MVP
  gold-set/              # размеченный eval-набор
data/corpus/             # ТЕКСТЫ документов для поиска (markdown)
  manifest.json          # doc_id → путь к файлу
  <source_id>/*.md
data/processed/          # выход пайплайна фазы 1
  documents.jsonl        # нормализованные документы (шаги 1–2)
  chunks.jsonl           # чанки для индекса (шаг 3)
phase-1-data/            # код пайплайна
phase-2-retrieval/       # embeddings, индекс, search, eval
phase-3-generation/      # /ask + цитаты
```
