from __future__ import annotations

from pathlib import Path

from sls.connectors.source_csv import read_csv_rows
from sls.core.normalize import normalize_email, normalize_phone, normalize_text
from sls.core.identity import lead_fingerprint


CRM_FIELD_RULES = {
    "external_id": ["external_id", "source_id", "lead_id", "id"],
    "contact.email": ["email", "e-mail", "mail"],
    "contact.phone": ["phone", "phone_number", "mobile", "tel", "telephone"],
    "contact.first_name": ["first_name", "firstname", "given_name", "name_first"],
    "contact.last_name": ["last_name", "lastname", "surname", "family_name", "name_last"],
    "contact.company": ["company", "company_name", "organization", "org"],
    "lead.source": ["source", "lead_source", "origin"],
    "lead.status": ["status", "lead_status", "state"],
}


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def suggest_field_mapping(headers: list[str]) -> dict:
    normalized_headers = {_normalize_header(h): h for h in headers}

    suggestions = []
    unmapped = []
    matched_headers: set[str] = set()

    for target_field, aliases in CRM_FIELD_RULES.items():
        match = None
        confidence = "low"

        for alias in aliases:
            alias_norm = _normalize_header(alias)
            if alias_norm in normalized_headers:
                match = normalized_headers[alias_norm]
                confidence = "high" if alias_norm == _normalize_header(target_field.split(".")[-1]) else "medium"
                matched_headers.add(match)
                break

        suggestions.append({
            "target_field": target_field,
            "source_column": match,
            "confidence": confidence if match else "none",
        })

    for original_header in headers:
        if original_header not in matched_headers:
            unmapped.append(original_header)

    return {
        "mapping_suggestions": suggestions,
        "unmapped_source_columns": unmapped,
        "note": "Suggestions are heuristic and should be reviewed before real CRM sync.",
    }


def build_data_quality_report(path: Path) -> dict:
    rows = read_csv_rows(path)

    missing_email = 0
    missing_phone = 0
    invalid_email = 0
    suspicious_phone = 0

    duplicate_emails: list[dict] = []
    duplicate_phones: list[dict] = []

    seen_emails: dict[str, str] = {}
    seen_phones: dict[str, str] = {}

    preview_issues: list[dict] = []

    for line_no, r in enumerate(rows, start=2):
        ext = normalize_text(r.get("external_id"))
        raw_email = normalize_text(r.get("email"))
        raw_phone = normalize_text(r.get("phone"))

        email_norm = normalize_email(raw_email)
        phone_norm = normalize_phone(raw_phone)
        fp = lead_fingerprint(ext, email_norm, phone_norm)

        row_issues: list[str] = []

        if not raw_email:
            missing_email += 1
            row_issues.append("missing_email")
        elif email_norm is None:
            invalid_email += 1
            row_issues.append("invalid_email")

        if not raw_phone:
            missing_phone += 1
            row_issues.append("missing_phone")
        else:
            if phone_norm is None or len(phone_norm.replace("+", "")) < 9:
                suspicious_phone += 1
                row_issues.append("suspicious_phone")

        if email_norm:
            if email_norm in seen_emails:
                duplicate_emails.append({
                    "line": line_no,
                    "external_id": ext,
                    "fingerprint": fp,
                    "duplicate_of": seen_emails[email_norm],
                })
                row_issues.append("duplicate_email")
            else:
                seen_emails[email_norm] = fp

        if phone_norm:
            if phone_norm in seen_phones:
                duplicate_phones.append({
                    "line": line_no,
                    "external_id": ext,
                    "fingerprint": fp,
                    "duplicate_of": seen_phones[phone_norm],
                })
                row_issues.append("duplicate_phone")
            else:
                seen_phones[phone_norm] = fp

        if row_issues:
            preview_issues.append({
                "line": line_no,
                "external_id": ext,
                "fingerprint": fp,
                "issues": row_issues,
            })

    headers = list(rows[0].keys()) if rows else []

    return {
        "input_path": str(path),
        "summary": {
            "rows_total": len(rows),
            "missing_email": missing_email,
            "missing_phone": missing_phone,
            "invalid_email": invalid_email,
            "suspicious_phone": suspicious_phone,
            "duplicate_email_count": len(duplicate_emails),
            "duplicate_phone_count": len(duplicate_phones),
        },
        "duplicates_preview": {
            "email": duplicate_emails[:20],
            "phone": duplicate_phones[:20],
        },
        "issues_preview": preview_issues[:50],
        "mapping_advisor": suggest_field_mapping(headers),
        "note": "Agent advisor report is local-only and avoids raw PII in output.",
    }


def build_dedupe_advisor_report(path: Path) -> dict:
    rows = read_csv_rows(path)

    normalized_rows: list[dict] = []

    for line_no, r in enumerate(rows, start=2):
        ext = normalize_text(r.get("external_id"))
        email_norm = normalize_email(normalize_text(r.get("email")))
        phone_norm = normalize_phone(normalize_text(r.get("phone")))
        first_name = normalize_text(r.get("first_name"))
        last_name = normalize_text(r.get("last_name"))
        company = normalize_text(r.get("company"))
        fp = lead_fingerprint(ext, email_norm, phone_norm)

        normalized_rows.append({
            "line": line_no,
            "external_id": ext,
            "fingerprint": fp,
            "email_norm": email_norm,
            "phone_norm": phone_norm,
            "first_name": first_name.lower() if first_name else None,
            "last_name": last_name.lower() if last_name else None,
            "company": company.lower() if company else None,
        })

    candidates: list[dict] = []

    for i in range(len(normalized_rows)):
        left = normalized_rows[i]

        for j in range(i + 1, len(normalized_rows)):
            right = normalized_rows[j]

            reasons: list[str] = []
            score = 0

            if left["email_norm"] and left["email_norm"] == right["email_norm"]:
                reasons.append("same_email")
                score += 100

            if left["phone_norm"] and left["phone_norm"] == right["phone_norm"]:
                reasons.append("same_phone")
                score += 90

            if (
                left["first_name"] and right["first_name"] and
                left["last_name"] and right["last_name"] and
                left["first_name"] == right["first_name"] and
                left["last_name"] == right["last_name"]
            ):
                reasons.append("same_full_name")
                score += 40

            if left["company"] and right["company"] and left["company"] == right["company"]:
                reasons.append("same_company")
                score += 20

            if score == 0:
                continue

            if score >= 100:
                confidence = "high"
            elif score >= 60:
                confidence = "medium"
            else:
                confidence = "low"

            candidates.append({
                "left": {
                    "line": left["line"],
                    "external_id": left["external_id"],
                    "fingerprint": left["fingerprint"],
                },
                "right": {
                    "line": right["line"],
                    "external_id": right["external_id"],
                    "fingerprint": right["fingerprint"],
                },
                "confidence": confidence,
                "score": score,
                "reasons": reasons,
            })

    candidates.sort(key=lambda x: (-x["score"], x["left"]["line"], x["right"]["line"]))

    return {
        "input_path": str(path),
        "summary": {
            "rows_total": len(rows),
            "candidate_pairs": len(candidates),
            "high_confidence": sum(1 for c in candidates if c["confidence"] == "high"),
            "medium_confidence": sum(1 for c in candidates if c["confidence"] == "medium"),
            "low_confidence": sum(1 for c in candidates if c["confidence"] == "low"),
        },
        "candidate_pairs_preview": candidates[:50],
        "note": "Dedupe advisor is heuristic, local-only, and avoids raw PII in output.",
    }