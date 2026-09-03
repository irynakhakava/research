---
id: pay-playbook-psp-timeout
title: "Playbook: таймауты PSP"
source_id: payments-confluence-ops
organization: NordLedger
language: ru
---

# Playbook: PSP timeout

Симптомы: рост `psp_request_timeouts`, пользовательские pending-платежи.

1. Проверьте status page PSP.
2. Включите feature flag `payments.psp_failover` если secondary PSP healthy.
3. Не ретрайте capture бесконечно — лимит 3.
4. Коммуникация: `#payments-help` + IC при Sev-2+.
