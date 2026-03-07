from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def load_db(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {"contacts": []}
    return json.loads(db_path.read_text(encoding="utf-8"))

def save_db(db_path: Path, db: dict[str, Any]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def find_by_external_id(db: dict[str, Any], external_id: str) -> dict[str, Any] | None:
    for c in db.get("contacts", []):
        if c.get("external_id") == external_id:
            return c
    return None

def find_by_email(db: dict[str, Any], email_norm: str) -> dict[str, Any] | None:
    for c in db.get("contacts", []):
        if c.get("email_norm") == email_norm:
            return c
    return None

def find_by_phone(db: dict[str, Any], phone_norm: str) -> dict[str, Any] | None:
    for c in db.get("contacts", []):
        if c.get("phone_norm") == phone_norm:
            return c
    return None

def upsert_contact(db: dict[str, Any], record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    # returns ("created"|"updated", contact)
    ext = record.get("external_id")
    if ext:
        existing = find_by_external_id(db, ext)
        if existing:
            existing.update(record)
            return "updated", existing

    em = record.get("email_norm")
    if em:
        existing = find_by_email(db, em)
        if existing:
            existing.update(record)
            return "updated", existing

    ph = record.get("phone_norm")
    if ph:
        existing = find_by_phone(db, ph)
        if existing:
            existing.update(record)
            return "updated", existing

    db.setdefault("contacts", []).append(record)
    return "created", record