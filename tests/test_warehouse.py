import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from src.etl.transform import transform_data
from src.etl.load import load_tables_to_warehouse
from src.warehouse.schema import initialize_database, get_table_counts

@pytest.fixture
def mock_dataset():
    return pd.DataFrame([
        {
            "id": 2001,
            "created_at": "2026-09-01 08:15:00 UTC",
            "event_type": "PushEvent",
            "developer": "dev_alpha",
            "repository": "corp/kubernetes-engine",
            "payload_json": '{"ref": "refs/heads/main"}',
        },
        {
            "id": 2002,
            "created_at": "2026-09-01 09:20:00 UTC",
            "event_type": "IssuesEvent",
            "developer": "dev_beta",
            "repository": "corp/kubernetes-engine",
            "payload_json": '{"action": "opened", "issue": {"title": "Pod crash fix", "comments": 3}}',
        },
        {
            "id": 2003,
            "created_at": "2026-09-01 10:45:00 UTC",
            "event_type": "PullRequestEvent",
            "developer": "bot-reviewer[bot]",
            "repository": "corp/frontend-react",
            "payload_json": '{"action": "opened"}',
        },
    ])

def test_warehouse_initialization_and_loading(tmp_path, mock_dataset):
    test_db = tmp_path / "test_warehouse.db"
    _, tables = transform_data(mock_dataset)

    counts = load_tables_to_warehouse(tables, db_path=test_db)
    assert counts["dim_time"] >= 1
    assert counts["dim_developer"] == 3
    assert counts["dim_repository"] == 2
    assert counts["dim_event"] >= 2
    assert counts["fact_github_activity"] == 3

    engine = create_engine(f"sqlite:///{test_db.as_posix()}")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM fact_github_activity")).scalar()
        assert res == 3
