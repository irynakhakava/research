---
id: sec-policy-secrets-handling
title: "Policy: обращение с секретами"
source_id: security-policies
organization: NordLedger
language: ru
---

# Secrets handling

- Секреты только в Vault / cloud secret manager.
- **Запрещено** хранить пароли БД и API keys в Confluence, Notion, git, Slack.
- Если секрет засветился — rotate в течение 1 часа и откройте SecOps incident.
