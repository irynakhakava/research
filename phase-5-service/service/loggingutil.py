"""JSON-логи запросов (NFR: trace_id, chunks, filters, models, refuse)."""

from __future__ import annotations

import json
import sys
import uuid
from typing import Any


def new_trace_id(header_value: str | None = None) -> str:
    raw = (header_value or "").strip()
    if raw:
        return raw[:128]
    return str(uuid.uuid4())


def log_event(payload: dict[str, Any]) -> None:
    sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stderr.flush()
