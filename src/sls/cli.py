from __future__ import annotations

import json
from pathlib import Path

import typer

from sls.core.plan import plan_from_csv
from sls.core.sync import sync_from_csv
from sls.core.retry import run_with_retry
from sls.core.normalize import normalize_email, normalize_phone, normalize_text
from sls.core.doctor import run_doctor

from sls.connectors.source_csv import read_csv_rows
from sls.connectors.target_fake_api import FakeApiClient
from sls.connectors.target_close import CloseConnector

from sls.agent.advisor import (
    build_data_quality_report,
    suggest_field_mapping,
    build_dedupe_advisor_report,
)

from sls.config.settings import Settings


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def plan(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    db_path: Path = typer.Option(Path("data/mock_crm/mock_db.json"), "--db"),
):
    """Compute sync plan."""
    result = plan_from_csv(input_csv, db_path=db_path)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def sync(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    db_path: Path = typer.Option(Path("data/mock_crm/mock_db.json"), "--db"),
):
    """Run sync."""
    result = sync_from_csv(input_csv, db_path=db_path)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("retry-demo")
def retry_demo():
    """Demo retry framework."""
    run_id = "retry_demo_run"
    client = FakeApiClient()

    result = run_with_retry(
        client.send_contact,
        run_id=run_id,
        operation_name="fake_api_send_contact",
        max_attempts=4,
    )

    typer.echo(
        json.dumps(
            {
                "run_id": run_id,
                "result": result,
                "calls_made": client.calls,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def advise(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
):
    """Run data quality advisor."""
    report = build_data_quality_report(input_csv)
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command("map-advise")
def map_advise(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
):
    """Suggest mapping from CSV columns to CRM fields."""
    rows = read_csv_rows(input_csv)
    headers = list(rows[0].keys()) if rows else []

    result = {
        "input_path": str(input_csv),
        "headers": headers,
        **suggest_field_mapping(headers),
    }

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("dedupe-advise")
def dedupe_advise(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
):
    """Suggest likely duplicate pairs from input CSV."""
    result = build_dedupe_advisor_report(input_csv)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("close-ping")
def close_ping():
    """Check Close CRM connector configuration."""
    settings = Settings.from_env()
    connector = CloseConnector.from_settings(settings)

    result = connector.ping()

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("close-plan")
def close_plan(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
):
    """Dry-run plan against Close CRM (no writes)."""
    settings = Settings.from_env()
    connector = CloseConnector.from_settings(settings)

    rows = read_csv_rows(input_csv)

    seen_external_ids: set[str] = set()
    seen_emails: set[str] = set()
    seen_phones: set[str] = set()

    plan = []
    summary = {
        "would_create": 0,
        "would_update_by_external_id": 0,
        "would_match_by_email": 0,
        "would_match_by_phone": 0,
    }

    for r in rows:
        contact = {
            "external_id": r.get("external_id"),
            "email": r.get("email"),
            "phone": r.get("phone"),
        }

        decision = connector.plan_contact(
            contact,
            seen_external_ids=seen_external_ids,
            seen_emails=seen_emails,
            seen_phones=seen_phones,
        )
        plan.append(decision)

        action = decision["action"]
        if action in summary:
            summary[action] += 1

        ext = normalize_text(r.get("external_id"))
        em = normalize_email(r.get("email"))
        ph = normalize_phone(r.get("phone"))

        if ext:
            seen_external_ids.add(ext)
        if em:
            seen_emails.add(em)
        if ph:
            seen_phones.add(ph)

    result = {
        "input_path": str(input_csv),
        "rows": len(rows),
        "summary": summary,
        "close_plan_preview": plan[:20],
        "note": "Dry run only — planner uses local matching heuristics, no Close API calls executed.",
    }

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("close-search-demo")
def close_search_demo(
    external_id: str | None = typer.Option(None, "--external-id"),
    email: str | None = typer.Option(None, "--email"),
    phone: str | None = typer.Option(None, "--phone"),
):
    """First read-only Close search demo. Provide one identifier."""
    settings = Settings.from_env()
    connector = CloseConnector.from_settings(settings)

    result = connector.search_contact(
        external_id=external_id,
        email=email,
        phone=phone,
    )

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("doctor")
def doctor(
    input_csv: Path | None = typer.Option(None, "--input", "-i"),
):
    """Check project health and configuration."""
    result = run_doctor(input_csv=input_csv)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("demo")
def demo(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    db_path: Path = typer.Option(Path("data/mock_crm/mock_db.json"), "--db"),
):
    """Run an end-to-end demo of the engine."""
    data_quality = build_data_quality_report(input_csv)
    sync_plan = plan_from_csv(input_csv, db_path=db_path)
    dedupe_report = build_dedupe_advisor_report(input_csv)
    doctor_report = run_doctor(input_csv=input_csv)

    close_demo: dict
    try:
        settings = Settings.from_env()
        connector = CloseConnector.from_settings(settings)

        rows = read_csv_rows(input_csv)

        seen_external_ids: set[str] = set()
        seen_emails: set[str] = set()
        seen_phones: set[str] = set()

        plan = []
        summary = {
            "would_create": 0,
            "would_update_by_external_id": 0,
            "would_match_by_email": 0,
            "would_match_by_phone": 0,
        }

        for r in rows:
            contact = {
                "external_id": r.get("external_id"),
                "email": r.get("email"),
                "phone": r.get("phone"),
            }

            decision = connector.plan_contact(
                contact,
                seen_external_ids=seen_external_ids,
                seen_emails=seen_emails,
                seen_phones=seen_phones,
            )
            plan.append(decision)

            action = decision["action"]
            if action in summary:
                summary[action] += 1

            ext = normalize_text(r.get("external_id"))
            em = normalize_email(r.get("email"))
            ph = normalize_phone(r.get("phone"))

            if ext:
                seen_external_ids.add(ext)
            if em:
                seen_emails.add(em)
            if ph:
                seen_phones.add(ph)

        close_demo = {
            "status": "ok",
            "summary": summary,
            "preview": plan[:10],
        }
    except Exception as e:
        close_demo = {
            "status": "skipped",
            "reason": type(e).__name__,
            "detail": str(e),
        }

    result = {
        "demo": "Secure Lead Synchronization Engine",
        "input_path": str(input_csv),
        "steps": {
            "doctor": doctor_report,
            "data_quality": {
                "summary": data_quality["summary"],
                "issues_preview": data_quality["issues_preview"][:5],
            },
            "plan": {
                "summary": sync_plan["summary"],
                "decisions_preview": sync_plan["decisions_preview"][:5],
            },
            "dedupe": {
                "summary": dedupe_report["summary"],
                "candidate_pairs_preview": dedupe_report["candidate_pairs_preview"][:5],
            },
            "close_plan": close_demo,
        },
        "note": "Demo mode runs local analysis and optional Close dry-run planning.",
    }

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()