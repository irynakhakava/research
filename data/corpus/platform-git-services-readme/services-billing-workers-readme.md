---
id: services-billing-workers-readme
title: "billing-workers README"
source_id: platform-git-services-readme
organization: NordLedger
language: ru
---

# billing-workers

Асинхронные воркеры биллинга NordLedger: выставление счетов, dunning, экспорт в ledger-core.

## Репозиторий

- **Git:** `https://git.nordledger.example/nordledger/services`  
- **Путь в monorepo:** `services/billing-workers/`  
- **Owner team:** Payments (+ Platform для деплоя)  
- **Pipeline:** `billing-deploy`

## Локальный запуск

```bash
cd services/billing-workers
make run-local
```

## Документация

- Runbooks деплоя: wiki PLAT → Runbooks  
- Контракты событий: `payments-contracts` (после MVP в индексе)
