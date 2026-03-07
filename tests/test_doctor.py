from pathlib import Path

from sls.core.doctor import run_doctor


def test_doctor_checks_csv_headers(tmp_path: Path):
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(
        (
            "external_id,email,phone,first_name,last_name,company,source,status\n"
            "web-1,jan@example.com,+420777123456,Jan,Novak,Acme,web,new\n"
        ),
        encoding="utf-8",
    )

    result = run_doctor(input_csv=csv_path)

    assert result["doctor_status"] in {"ok", "warning"}
    header_check = next(c for c in result["checks"] if c["check"] == "input_csv_headers")
    assert header_check["status"] == "ok"
    assert header_check["detail"]["missing_required_columns"] == []