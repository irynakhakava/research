---
id: data-airflow-backfill
title: "Airflow: backfill"
source_id: data-git-airflow-runbooks
organization: NordLedger
language: ru
---

# Backfill

```bash
airflow dags backfill -s 2026-07-01 -e 2026-07-07 <dag_id>
```

Делайте backfill в off-peak. Для больших диапазонов дробите по неделям.
