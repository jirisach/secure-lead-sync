from __future__ import annotations

from pathlib import Path

from sls.config.settings import Settings
from sls.connectors.source_csv import read_csv_rows


REQUIRED_CSV_COLUMNS = {
    "external_id",
    "email",
    "phone",
    "first_name",
    "last_name",
    "company",
    "source",
    "status",
}


def run_doctor(input_csv: Path | None = None) -> dict:
    settings = Settings.from_env()

    checks: list[dict] = []

    project_root = Path(".")
    checks.append({
        "check": "project_root_exists",
        "status": "ok" if project_root.exists() else "error",
        "detail": str(project_root.resolve()),
    })

    checks.append({
        "check": "close_api_key_present",
        "status": "ok" if settings.close_api_key else "warning",
        "detail": "CLOSE_API_KEY is set" if settings.close_api_key else "CLOSE_API_KEY is missing",
    })

    checks.append({
        "check": "close_base_url_valid",
        "status": "ok" if settings.close_base_url.startswith("https://") else "error",
        "detail": settings.close_base_url,
    })

    state_path = Path("data/state/sync_state.json")
    checks.append({
        "check": "state_file_exists",
        "status": "ok" if state_path.exists() else "warning",
        "detail": str(state_path),
    })

    log_path = Path("data/logs/sls.log.jsonl")
    checks.append({
        "check": "log_file_exists",
        "status": "ok" if log_path.exists() else "warning",
        "detail": str(log_path),
    })

    if input_csv is not None:
        if not input_csv.exists():
            checks.append({
                "check": "input_csv_exists",
                "status": "error",
                "detail": str(input_csv),
            })
        else:
            checks.append({
                "check": "input_csv_exists",
                "status": "ok",
                "detail": str(input_csv),
            })

            rows = read_csv_rows(input_csv)
            headers = set(rows[0].keys()) if rows else set()
            missing = sorted(REQUIRED_CSV_COLUMNS - headers)

            checks.append({
                "check": "input_csv_headers",
                "status": "ok" if not missing else "error",
                "detail": {
                    "rows": len(rows),
                    "missing_required_columns": missing,
                },
            })

    overall_status = "ok"
    if any(c["status"] == "error" for c in checks):
        overall_status = "error"
    elif any(c["status"] == "warning" for c in checks):
        overall_status = "warning"

    return {
        "doctor_status": overall_status,
        "checks": checks,
    }