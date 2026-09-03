---
id: pm-2026-03-gateway-timeout
title: "Postmortem 2026-03: gateway timeouts"
source_id: sre-drive-postmortems
organization: NordLedger
language: ru
---

# Postmortem: api-gateway timeouts (2026-03-12)

**Impact:** Sev-2, 18 минут, повышенные 504.  
**Cause:** connection pool exhaustion после релиза gateway.  
**Fix:** rollback + увеличение pool + лимит concurrency.  
**Follow-up:** load test обязателен для gateway-deploy.
