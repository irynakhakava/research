---
id: plat-runbook-k8s-debug
title: "Базовая диагностика Kubernetes в Platform"
source_id: platform-confluence-runbooks
organization: NordLedger
language: ru
---

# Базовая диагностика Kubernetes (Platform)

## Минимальный набор команд

```bash
kubectl config use-context nl-staging   # или nl-prod (только с approval)
kubectl -n <ns> get pods -o wide
kubectl -n <ns> describe pod <pod>
kubectl -n <ns> logs <pod> --previous --tail=200
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -n 30
```

## Интерпретация статусов

| Статус | Что проверить |
|--------|----------------|
| CrashLoopBackOff | логи `--previous`, exit code |
| ImagePullBackOff | registry auth / tag |
| Pending | ресурсы нод, PVC |
| OOMKilled | memory limits, heap |

Подробные playbooks сервисов живут рядом в Runbooks/.
