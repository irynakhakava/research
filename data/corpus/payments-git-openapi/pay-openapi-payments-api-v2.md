---
id: pay-openapi-payments-api-v2
title: "OpenAPI payments-api v2 (summary)"
source_id: payments-git-openapi
organization: NordLedger
language: ru
---

# payments-api v2 — summary

Базовый путь: `/v2/payments`

- `POST /v2/payments` — создать платёж
- `GET /v2/payments/{id}` — статус
- Auth: Bearer API key, scope `payments:write` / `payments:read`

Полный YAML: `openapi/payments-api-v2.yaml` в репо `payments-contracts`.
