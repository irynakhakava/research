---
id: plat-arch-service-mesh-overview
title: "Internal service mesh NordLedger — overview"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# Internal service mesh NordLedger

## Простыми словами

У нас сервисы в Kubernetes ходят друг к другу не «напрямую как попало», а через **service mesh** (на базе sidecar-прокси).  
Рядом с каждым подом работает маленький proxy, который:

- шифрует трафик (mTLS) между сервисами;
- добавляет retries/timeouts по единым правилам;
- отдаёт метрики «кто к кому ходил».

Приложению обычно не нужно знать детали: оно ходит на обычный DNS-имя сервиса (`payments-api.payments.svc`), а mesh делает остальное.

## Зачем sidecars

- Единая безопасность без правок кода каждого сервиса.
- Единые таймауты (дефолт 5s) и circuit breaking.
- Трассировки span’ов на hop’ах.

## Что не делает mesh

- Не заменяет api-gateway для внешнего трафика.
- Не хранит секреты (это Vault).
