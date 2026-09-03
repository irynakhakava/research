# Нефункциональные требования (NFR)

Связанный туториал: [Шаг 3](../docs/tutorials/00-discovery.md#шаг-3-нефункциональные-требования-nfr)

Значения ниже — разумный стартовый черновик. Пометьте `TBD` там, где нужно решение stakeholders, и поставьте дату.

## Таблица целей

| ID | Требование | Цель MVP | Как измеряем | Статус |
|----|------------|----------|--------------|--------|
| NFR-1 | Latency `/search` | p95 ≤ 500 ms | APM / OpenTelemetry | draft |
| NFR-2 | Latency `/ask` (retrieve+LLM) | p95 ≤ 5 s | APM | draft |
| NFR-3 | Freshness индекса | после изменения файлов в `data/corpus` достаточно пересобрать индекс (нет внешнего sync) | пересборка индекса в пайплайне / CI | draft |
| NFR-4 | Availability | 99.5% monthly (без учёта LLM provider outage) | uptime checks | TBD — решить до |
| NFR-5 | ACL | чанк не покидает сервис, если user/token не проходит фильтр | negative ACL tests | draft |
| NFR-6 | Multi-tenancy | фильтр по `team` / `space` из claims | integration tests | draft |
| NFR-7 | Cost control | ≤ $X / 1k `/ask` (или внутренние GPU-часы) | cost dashboard | TBD |
| NFR-8 | Privacy | секреты/токены в ответе редact'ятся | regex + spot checks | draft |

## Политика при низкой уверенности

Если retrieval пустой или top-score ниже порога:

1. **Не** генерировать «общий» ответ из параметров модели.  
2. Вернуть `refuse` / предложить переформулировать / показать ближайшие документы без синтеза (выбор зафиксировать в ADR).  
3. Залогировать кейс для пополнения gold-set.

**Выбранная политика MVP:** `refuse_with_nearest_links`  
(сгенерировать короткий отказ + до 3 ссылок на ближайшие документы без утверждений «фактов»).

## Безопасность и доступ

- Фильтрация ACL выполняется **до** передачи чанков в LLM.  
- Сервисный токен без user claims не получает `need-to-know` источники.  
- Промпт и логи не должны сохранять сырые secrets из документов (redaction pipeline — фаза 1/5).

## Наблюдаемость (минимум)

На каждый запрос обязательны поля лога/трейса:

- `trace_id`
- `user_id` / `service_principal` (хеш, если нужно)
- `retrieved_chunk_ids[]`
- `filters_applied`
- `embedding_model`, `llm_model`
- `refuse: bool`

## Открытые вопросы

1. Какой IdP и формат ACL claims? → TBD  
2. Нужен ли отдельный индекс на команду или один индекс с фильтрами? → TBD (рекомендация: один индекс + metadata filter)  
3. Допустимы ли облачные embeddings/LLM для внутренних доков? → TBD  
