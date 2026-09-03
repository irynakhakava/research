---
id: plat-runbook-deploy-overview
title: "Обзор деплоя сервисов Platform"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# Обзор деплоя сервисов Platform

## Модель релизов

Каждый сервис из monorepo `nordledger/services` деплоится отдельным pipeline:

| Сервис | Pipeline | Canary | Rollback job |
|--------|----------|--------|--------------|
| payments-api | payments-deploy | 10% → 100% | rollback:staging / rollback:production |
| payments-worker | payments-deploy | нет (blue/green) | rollback:* |
| api-gateway | gateway-deploy | 5% → 100% | rollback:* |
| billing-workers | billing-deploy | нет | rollback:* |

## Артефакты

- Образ: `registry.nordledger.example/<service>:<gitsha>`
- Deploy artifact хранит предыдущие 20 SHA на среду.
- Для staging откат разрешён дежурному Platform; для prod — IC + Payments lead.

## Чеклист перед деплоем в staging

1. CI green на main.
2. Миграции БД совместимы backward (expand/contract).
3. Feature flags выключены по умолчанию.
