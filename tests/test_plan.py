from pathlib import Path

from sls.core.plan import plan_from_csv
from sls.connectors.target_mock import save_db


def test_plan_detects_duplicates_and_creates(tmp_path: Path):
    csv_path = tmp_path / "input.csv"
    db_path = tmp_path / "mock_db.json"

    csv_path.write_text(
        (
            "external_id,email,phone,first_name,last_name,company,source,status\n"
            "web-1,jan@example.com,+420777123456,Jan,Novak,Acme,web,new\n"
            "web-2,jan2@example.com,+420777123456,Jan,Novak,Acme,web,new\n"
            "web-3,anna@example.com,+14155550101,Anna,Lee,Acme,web,new\n"
        ),
        encoding="utf-8",
    )

    save_db(db_path, {"contacts": []})

    result = plan_from_csv(csv_path, db_path=db_path)

    assert result["rows_total"] == 3
    assert result["summary"]["creates"] == 2
    assert result["summary"]["duplicates_in_input"] == 1