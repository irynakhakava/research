---
id: plat-runbook-gateway-auth
title: "API Gateway: аутентификация и ошибки 401/403"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# API Gateway: аутентификация и 401/403

## Как работает auth

1. Клиент передаёт `Authorization: Bearer <api_key>` или mTLS.
2. api-gateway проверяет ключ в identity-service (`/v1/keys/validate`).
3. При успехе прокидывается заголовок `X-NL-Service` и ACL scopes.

## 403 после ротации ключей — куда смотреть

1. Убедитесь, что **новый** ключ активирован в identity-service (статус `active`), а не только создан.
2. Проверьте, что клиент обновил секрет в Vault path `secret/services/<client>/api_key` и сделал reload.
3. На gateway смотрите логи: `auth_denied reason=key_revoked|scope_missing|unknown_key`.
4. Частая ошибка: в staging оставили старый ключ, в prod уже revoke — см. [ротацию ключей](plat-runbook-key-rotation.md).
5. Проверка вручную:
   ```bash
   curl -i https://gateway.staging.nordledger.example/v1/health      -H "Authorization: Bearer $API_KEY"
   ```
   Ожидаем 200. Если 403 — ключ/scopes; если 401 — формат заголовка.

## Не путать

- 401 = нет/битый токен  
- 403 = токен есть, но нет права / ключ отозван
