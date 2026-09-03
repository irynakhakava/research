# Корпус документации (статический)

Тексты, **по которым система будет искать ответы**.  
Это **единственный** источник контента в проекте: реальных Confluence/Git подключений нет.

Вымышленная орг. NordLedger.

## Структура

```
data/corpus/
  manifest.json          # индекс: doc_id → путь
  <source_id>/
    <doc_id>.md          # содержимое страницы
```

Папки соответствуют `id` источников из `phase-0-discovery/sources.catalog.yaml`.

## Состав

- Все `sample_doc_ids` из каталога источников  
- Документы из `relevant_doc_ids` gold-set (включая `plat-runbook-deploy-overview`)

Всего: см. `manifest.json` → поле `documents`.

## Как искать вручную

```bash
# найти файл по id
jq -r '.documents[] | select(.id=="plat-runbook-payments-rollback") | .path' data/corpus/manifest.json

# полный текст
cat data/corpus/platform-confluence-runbooks/plat-runbook-payments-rollback.md
```

## Связь с gold-set

Вопрос из `phase-0-discovery/gold-set/dataset.jsonl` ссылается на `relevant_doc_ids` — эти id должны существовать здесь как `<doc_id>.md`.
