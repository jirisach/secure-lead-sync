from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from sls.observability.redaction import redact_payload


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log_event(event: str, run_id: str, payload: dict[str, Any] | None = None) -> None:
    payload = payload or {}
    safe_payload = redact_payload(payload)

    record = {
        "timestamp": utc_now_iso(),
        "event": event,
        "run_id": run_id,
        **safe_payload,
    }

    log_path = Path("data/logs/sls.log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")