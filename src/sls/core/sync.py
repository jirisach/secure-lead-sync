from __future__ import annotations

from pathlib import Path

from sls.connectors.source_csv import read_csv_rows
from sls.connectors.target_mock import load_db, save_db, upsert_contact
from sls.core.normalize import normalize_email, normalize_phone, normalize_text
from sls.core.identity import lead_fingerprint
from sls.core.state import make_run_id, save_state, utc_now_iso
from sls.observability.logging import log_event


def sync_from_csv(path: Path, db_path: Path) -> dict:
    rows = read_csv_rows(path)
    db = load_db(db_path)

    created = 0
    updated = 0
    errors: list[dict] = []

    run_id = make_run_id()
    run_at = utc_now_iso()

    log_event(
        "run_started",
        run_id,
        {
            "input_path": str(path),
            "db_path": str(db_path),
            "rows_total": len(rows),
        },
    )

    for i, r in enumerate(rows, start=2):
        ext = normalize_text(r.get("external_id"))
        if not ext:
            errors.append({"line": i, "error": "missing_external_id"})
            log_event(
                "record_error",
                run_id,
                {
                    "line": i,
                    "error": "missing_external_id",
                },
            )
            continue

        email_norm = normalize_email(r.get("email"))
        phone_norm = normalize_phone(r.get("phone"))
        fp = lead_fingerprint(ext, email_norm, phone_norm)

        record = {
            "external_id": ext,
            "email_norm": email_norm,
            "phone_norm": phone_norm,
            "first_name": normalize_text(r.get("first_name")),
            "last_name": normalize_text(r.get("last_name")),
            "company": normalize_text(r.get("company")),
            "source": normalize_text(r.get("source")),
            "status": normalize_text(r.get("status")),
            "fingerprint": fp,
        }

        action, _ = upsert_contact(db, record)

        if action == "created":
            created += 1
        else:
            updated += 1

        log_event(
            "record_synced",
            run_id,
            {
                "line": i,
                "external_id": ext,
                "fingerprint": fp,
                "action": action,
                "source": record.get("source"),
                "status": record.get("status"),
                "email": record.get("email_norm"),
                "phone": record.get("phone_norm"),
                "first_name": record.get("first_name"),
                "last_name": record.get("last_name"),
            },
        )

    save_db(db_path, db)

    state_path = Path("data/state/sync_state.json")
    state = {
        "last_run_id": run_id,
        "last_run_at": run_at,
        "last_input_path": str(path),
        "last_db_path": str(db_path),
        "last_summary": {
            "rows_total": len(rows),
            "created": created,
            "updated": updated,
            "errors": len(errors),
        },
    }
    save_state(state_path, state)

    log_event(
        "run_finished",
        run_id,
        {
            "input_path": str(path),
            "db_path": str(db_path),
            "state_path": str(state_path),
            "rows_total": len(rows),
            "created": created,
            "updated": updated,
            "errors": len(errors),
        },
    )

    return {
        "run_id": run_id,
        "run_at": run_at,
        "input_path": str(path),
        "db_path": str(db_path),
        "state_path": str(state_path),
        "rows_total": len(rows),
        "created": created,
        "updated": updated,
        "errors": errors[:50],
    }