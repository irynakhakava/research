---
id: sre-guide-rollback-decision
title: "Когда откатывать релиз"
source_id: sre-notion-incident-guides
organization: NordLedger
language: ru
---

# Rollback decision guide

Откатывайте, если:

- ошибка связана с последним деплоем (< 2h) и есть простой rollback path;
- mitigate без отката займёт > 30 минут при Sev-1/Sev-2.

Не откатывайте «на всякий случай», если корневая причина — зависимость (PSP, cloud region).
