---
id: plat-runbook-payments-rollback
title: "Runbook: откат релиза payments (staging / prod)"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# Runbook: откат релиза payments

**Владелец:** Platform On-call · **Сервис:** payments-api, payments-worker  
**Среды:** staging, production

## Когда применять

- После неудачного деплоя (рост 5xx, ошибки settlement, регрессия в canary).
- По решению Incident Commander / дежурного Payments.

## Staging: быстрый rollback

1. Откройте pipeline **payments-deploy** в GitLab CI.
2. Найдите последний успешный deploy artifact для `staging` (job `deploy:staging`).
3. Запустите manual job **`rollback:staging`** и укажите `ARTIFACT_SHA` предыдущего релиза.
4. Дождитесь `healthcheck:staging` = green (readiness `/readyz` у payments-api).
5. Проверьте метрики 5 минут: `payments_http_5xx_rate`, `payments_settlement_lag`.

```bash
# альтернатива из laptop (нужен kubecontext staging)
kubectl -n payments rollout undo deploy/payments-api
kubectl -n payments rollout undo deploy/payments-worker
kubectl -n payments rollout status deploy/payments-api
```

## Production

1. Объявите инцидент (см. SRE severity).
2. Rollback только через pipeline `rollback:production` (запрещён raw kubectl без IC).
3. После отката — postmortem в течение 48 часов.

## Связанные документы

- [Обзор деплоя](plat-runbook-deploy-overview.md)
- [CrashLoop payments](plat-runbook-payments-crashloop.md)
