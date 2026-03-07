from pathlib import Path

from sls.agent.advisor import build_data_quality_report, build_dedupe_advisor_report


def test_data_quality_report_counts_issues(tmp_path: Path):
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(
        (
            "external_id,email,phone,first_name,last_name,company,source,status\n"
            "web-1,jan@example.com,+420777123456,Jan,Novak,Acme,web,new\n"
            "web-2,,+420777123456,Jan,Novak,Acme,web,new\n"
            "web-3,bad-email,,Anna,Lee,Acme,web,new\n"
        ),
        encoding="utf-8",
    )

    report = build_data_quality_report(csv_path)

    assert report["summary"]["rows_total"] == 3
    assert report["summary"]["missing_email"] == 1
    assert report["summary"]["missing_phone"] == 1
    assert report["summary"]["invalid_email"] == 1
    assert report["summary"]["duplicate_phone_count"] == 1


def test_dedupe_advisor_finds_candidate_pairs(tmp_path: Path):
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(
        (
            "external_id,email,phone,first_name,last_name,company,source,status\n"
            "web-1,jan@example.com,+420777123456,Jan,Novak,Acme,web,new\n"
            "web-2,jan@example.com,+420777123456,Jan,Novak,Acme,web,new\n"
        ),
        encoding="utf-8",
    )

    report = build_dedupe_advisor_report(csv_path)

    assert report["summary"]["candidate_pairs"] >= 1
    assert report["summary"]["high_confidence"] >= 1