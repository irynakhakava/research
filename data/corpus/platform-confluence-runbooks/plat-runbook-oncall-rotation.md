---
id: plat-runbook-oncall-rotation
title: "Как добавить человека в on-call ротацию Platform"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# On-call ротация Platform

## Добавить участника

1. У человека должен быть доступ к PagerDuty schedule **Platform Primary**.
2. Заведите заявку в Jira `PLAT` типа «On-call access» (или попросите лида в `#platform-docs`).
3. После approve SRE/Platform lead добавит user в:
   - PagerDuty → Schedule `platform-primary`
   - Slack user group `@platform-oncall`
   - Vault policy `oncall-platform-read`
4. Новичок обязан пройти shadow-shift (один weekend shadow) до самостоятельной недели.
5. Обновите календарь: Notion страница «Platform On-call calendar».

## Снять с ротации

Тот же тикет с типом remove + дата последней смены.
