---
id: plat-runbook-payments-crashloop
title: "Troubleshooting: KubePodCrashLooping на payments"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# Troubleshooting: KubePodCrashLooping на payments

Алерт: `KubePodCrashLooping` namespace `payments`, deploy `payments-api` или `payments-worker`.

## С чего начать (порядок)

1. **События и логи контейнера**
   ```bash
   kubectl -n payments describe pod -l app=payments-api | tail -n 40
   kubectl -n payments logs -l app=payments-api --previous --tail=200
   ```
2. **Частые причины**
   - Недоступен Vault/секреты → смотрите `FailedMount` / `secret not found`.
   - Падение на миграции → в логах `liquibase lock` или `migration failed`.
   - Неверный `DATABASE_URL` после ротации → см. key-rotation runbook.
   - OOMKilled → увеличьте limit временно, откройте тикет на capacity.
3. **Зависимости**
   - Postgres `payments-db` (проверка: `pg_isready` из debug pod).
   - api-gateway не обязан быть up для worker, но api зависит от identity-service.
4. Если pod не поднимается > 15 минут — рассмотрите [rollback](plat-runbook-payments-rollback.md).

## Эскалация

- Payments on-call → `#payments-help`
- Если кластерный сбой — SRE on-call
