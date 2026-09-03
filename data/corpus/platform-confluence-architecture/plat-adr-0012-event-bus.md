---
id: plat-adr-0012-event-bus
title: "ADR-0012: Event bus на Kafka"
source_id: platform-confluence-architecture
organization: NordLedger
language: ru
---

# ADR-0012: Event bus

Статус: accepted.

Решение: межсервисные доменные события — через Kafka cluster `nl-events`.  
Синхронный HTTP оставляем для request/response API.
