from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "email",
    "phone",
    "first_name",
    "last_name",
    "name",
    "full_name",
    "notes",
    "address",
}


def redact_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in SENSITIVE_KEYS:
        return "[REDACTED]"
    return value


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: redact_value(k, v) for k, v in payload.items()}