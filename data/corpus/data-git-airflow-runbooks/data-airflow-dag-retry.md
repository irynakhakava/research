---
id: data-airflow-dag-retry
title: "Airflow: безопасный retry DAG"
source_id: data-git-airflow-runbooks
organization: NordLedger
language: ru
---

# Airflow: retry DAG

```bash
airflow dags clear <dag_id> --start-date <ds> --end-date <ds>
```

Не clear'ьте mid-run без проверки downstream tables. Для ledger exports используйте marked rerun job.
