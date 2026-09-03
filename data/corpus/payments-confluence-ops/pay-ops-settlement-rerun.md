---
id: pay-ops-settlement-rerun
title: "Operations: повторный запуск settlement"
source_id: payments-confluence-ops
organization: NordLedger
language: ru
---

# Повторный запуск settlement

## Когда нужно

Settlement batch упал или частично завершился (`settlement_lag > 30m`).

## Шаги

1. Проверьте статус batch в админке Payments → Settlements.
2. Убедитесь, что нет активного lock в Redis key `settlement:lock`.
3. Запустите job `settlement-rerun` с `batch_id`.
4. Не запускайте два rerun параллельно.

При PSP timeout см. playbook PSP.
