---
id: data-airflow-stuck-task
title: "Airflow: зависшая task"
source_id: data-git-airflow-runbooks
organization: NordLedger
language: ru
---

# Stuck task

1. UI → Task Instance → see log heartbeats.
2. Если worker dead — mark failed и clear.
3. Проверьте очередь Celery/`kubernetes` executor pods.
