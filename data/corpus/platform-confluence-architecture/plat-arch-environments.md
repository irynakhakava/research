---
id: plat-arch-environments
title: "Окружения: staging vs preprod vs prod"
source_id: platform-confluence-architecture
organization: NordLedger
language: ru
---

# Окружения NordLedger

| Env | Назначение | Данные |
|-----|------------|--------|
| staging | интеграция и QA | синтетика |
| preprod | прогон релизов | обезличенный срез |
| production | бой | боевые |

Staging ≠ preprod: в preprod включены те же лимиты rate-limit, что в prod.
