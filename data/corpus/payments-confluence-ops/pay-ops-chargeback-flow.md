---
id: pay-ops-chargeback-flow
title: "Operations: поток chargeback"
source_id: payments-confluence-ops
organization: NordLedger
language: ru
---

# Chargeback flow

1. Уведомление от PSP попадает в `payments-worker` topic `psp.chargebacks`.
2. Создаётся кейс в Jira PAY с приоритетом по сумме.
3. Аналитик подтверждает в Ops UI; воркер делает reverse в ledger-core.

Не обрабатывайте chargeback вручную SQL в prod.
