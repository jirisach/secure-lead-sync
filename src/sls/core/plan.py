from __future__ import annotations

from pathlib import Path

from sls.connectors.source_csv import read_csv_rows
from sls.connectors.target_mock import load_db, find_by_external_id, find_by_email, find_by_phone
from sls.core.normalize import normalize_email, normalize_phone, normalize_text
from sls.core.identity import lead_fingerprint
from sls.core.state import load_state


def plan_from_csv(path: Path, db_path: Path) -> dict:
    rows = read_csv_rows(path)

    # Load mock target DB if exists, else empty
    db = load_db(db_path)

    # Load last sync state if exists
    state_path = Path("data/state/sync_state.json")
    state = load_state(state_path)

    errors: list[dict] = []
    decisions: list[dict] = []

    creates = 0
    updates = 0
    duplicates = 0
    skips = 0

    # Detect duplicates within the SAME input (no PII stored)
    seen_emails: dict[str, str] = {}  # email_norm -> fingerprint(first)
    seen_phones: dict[str, str] = {}  # phone_norm -> fingerprint(first)

    for line_no, r in enumerate(rows, start=2):  # header is line 1
        ext = normalize_text(r.get("external_id"))
        if not ext:
            errors.append({"line": line_no, "error": "missing_external_id"})
            continue

        email_norm = normalize_email(r.get("email"))
        phone_norm = normalize_phone(r.get("phone"))
        fp = lead_fingerprint(ext, email_norm, phone_norm)

        # 1) Duplicate detection within input
        dupe_reason = None
        dupe_of = None

        if email_norm:
            if email_norm in seen_emails:
                dupe_reason = "duplicate_in_input_email"
                dupe_of = seen_emails[email_norm]
            else:
                seen_emails[email_norm] = fp

        if (dupe_reason is None) and phone_norm:
            if phone_norm in seen_phones:
                dupe_reason = "duplicate_in_input_phone"
                dupe_of = seen_phones[phone_norm]
            else:
                seen_phones[phone_norm] = fp

        if dupe_reason:
            duplicates += 1
            decisions.append({
                "line": line_no,
                "external_id": ext,
                "fingerprint": fp,
                "decision": "duplicate",
                "reason": dupe_reason,
                "duplicate_of": dupe_of,
            })
            continue

        # 2) Target matching (mock DB) => create/update/skip
        match = None
        match_reason = None

        # Prefer stable external_id
        existing = find_by_external_id(db, ext)
        if existing:
            match = existing
            match_reason = "match_external_id"
        elif email_norm:
            existing = find_by_email(db, email_norm)
            if existing:
                match = existing
                match_reason = "match_email"
        elif phone_norm:
            existing = find_by_phone(db, phone_norm)
            if existing:
                match = existing
                match_reason = "match_phone"

        if match:
            updates += 1
            decisions.append({
                "line": line_no,
                "external_id": ext,
                "fingerprint": fp,
                "decision": "update",
                "reason": match_reason,
            })
        else:
            creates += 1
            decisions.append({
                "line": line_no,
                "external_id": ext,
                "fingerprint": fp,
                "decision": "create",
                "reason": "no_match",
            })

    return {
        "input_path": str(path),
        "db_path": str(db_path),
        "rows_total": len(rows),
        "rows_ok": len(rows) - len(errors),
        "rows_error": len(errors),
        "summary": {
            "creates": creates,
            "updates": updates,
            "duplicates_in_input": duplicates,
            "skips": skips,
        },
        "errors": errors[:50],
        "decisions_preview": decisions[:50],
        "last_run": state,
        "note": "Phase 3: plan includes mock target diff, duplicate detection inside input, and last run state (no PII).",
    }