import pytest
import pandas as pd
from sqlalchemy import create_engine

from src.etl.transform import transform_data
from src.etl.load import load_tables_to_warehouse
from src.warehouse.queries import (
    olap_rollup,
    olap_drilldown,
    olap_slice,
    olap_dice,
    olap_pivot,
)

@pytest.fixture
def populated_engine(tmp_path):
    test_db = tmp_path / "test_olap.db"
    mock_df = pd.DataFrame([
        {
            "id": 3001,
            "created_at": "2026-09-01 08:00:00 UTC",
            "event_type": "PushEvent",
            "developer": "dev1",
            "repository": "group/docker-app",
            "payload_json": '{"ref": "refs/heads/main"}',
        },
        {
            "id": 3002,
            "created_at": "2026-09-01 08:30:00 UTC",
            "event_type": "IssuesEvent",
            "developer": "dev2",
            "repository": "group/docker-app",
            "payload_json": '{"action": "opened", "issue": {"title": "Crash on boot", "comments": 1}}',
        },
        {
            "id": 3003,
            "created_at": "2026-09-01 09:00:00 UTC",
            "event_type": "PullRequestEvent",
            "developer": "dev3",
            "repository": "group/react-ui",
            "payload_json": '{"action": "opened"}',
        },
        {
            "id": 3004,
            "created_at": "2026-09-01 09:30:00 UTC",
            "event_type": "PushEvent",
            "developer": "bot[bot]",
            "repository": "group/react-ui",
            "payload_json": '{"ref": "refs/heads/main"}',
        },
    ])
    _, tables = transform_data(mock_df)
    load_tables_to_warehouse(tables, db_path=test_db)
    return create_engine(f"sqlite:///{test_db.as_posix()}")

def test_olap_rollup(populated_engine):
    df_rollup = olap_rollup(populated_engine, group_by="hour")
    assert not df_rollup.empty
    assert "total_events" in df_rollup.columns
    assert df_rollup["total_events"].sum() == 4

def test_olap_drilldown(populated_engine):
    df_drill = olap_drilldown(populated_engine, target_date="2026-09-01")
    assert not df_drill.empty
    assert "event_count" in df_drill.columns
    assert "event_type" in df_drill.columns

def test_olap_slice(populated_engine):
    df_slice = olap_slice(populated_engine, dimension="event_type", value="PushEvent")
    assert not df_slice.empty
    assert (df_slice["event_type"] == "PushEvent").all()
    assert df_slice["activity_count"].sum() == 2

def test_olap_dice(populated_engine):
    df_dice = olap_dice(populated_engine, event_types=["PushEvent", "IssuesEvent"], hour_range=(8, 10))
    assert not df_dice.empty
    assert df_dice["event_count"].sum() == 3

def test_olap_pivot(populated_engine):
    df_piv = olap_pivot(populated_engine, row_dimension="category", column_dimension="event_type")
    assert not df_piv.empty
    assert "PushEvent" in df_piv.columns
