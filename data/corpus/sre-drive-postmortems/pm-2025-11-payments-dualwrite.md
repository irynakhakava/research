---
id: pm-2025-11-payments-dualwrite
title: "Postmortem 2025-11: payments dual-write"
source_id: sre-drive-postmortems
organization: NordLedger
language: ru
---

# Postmortem: payments dual-write (2025-11-03)

**Impact:** Sev-1, расхождение ledger vs payments-db.  
**Cause:** dual-write без outbox.  
**Fix:** feature flag off + reconcile job.  
**Lesson:** новые write-path только через outbox pattern (см. ADR-0012).
