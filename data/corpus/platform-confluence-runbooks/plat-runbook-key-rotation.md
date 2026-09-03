---
id: plat-runbook-key-rotation
title: "Ротация API ключей сервисов"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# Ротация API ключей

## Процедура (overlap)

1. Создайте новый ключ в identity-service (`status=active`, тот же scope).
2. Положите новый ключ в Vault **рядом** со старым (`api_key_next`).
3. Обновите consumer (деплой или hot-reload).
4. Дождитесь трафика на новый ключ (метрика `identity_key_usage`).
5. Переведите старый ключ в `revoked`.
6. Удалите `api_key_next` после стабилизации 24h.

## Если сразу отозвали старый ключ

Клиенты получат **403** на api-gateway. Временно верните статус `active` старому ключу либо ускорьте выкладку нового у consumer.

Секреты и пароли БД в этой документации **не публикуются** — только пути Vault.
