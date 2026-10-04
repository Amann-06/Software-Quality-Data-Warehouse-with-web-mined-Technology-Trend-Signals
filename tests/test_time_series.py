import pytest
import pandas as pd

from src.mining.time_series import (
    prepare_datetime_index,
    compute_hourly_activity,
    compute_event_type_series,
    compute_category_series,
    compute_trend_summary,
)

@pytest.fixture
def mock_ts_dataframe():
    return pd.DataFrame([
        {
            "id": 1,
            "created_at_dt": pd.to_datetime("2026-09-01 08:10:00 UTC"),
            "event_type": "PushEvent",
            "developer": "alice",
            "repository": "repo1",
            "technology_category": "DevOps",
            "is_defect_proxy": 0,
        },
        {
            "id": 2,
            "created_at_dt": pd.to_datetime("2026-09-01 08:40:00 UTC"),
            "event_type": "IssuesEvent",
            "developer": "bob",
            "repository": "repo1",
            "technology_category": "DevOps",
            "is_defect_proxy": 1,
        },
        {
            "id": 3,
            "created_at_dt": pd.to_datetime("2026-09-01 09:15:00 UTC"),
            "event_type": "PushEvent",
            "developer": "charlie",
            "repository": "repo2",
            "technology_category": "Web",
            "is_defect_proxy": 0,
        },
        {
            "id": 4,
            "created_at_dt": pd.to_datetime("2026-09-01 10:20:00 UTC"),
            "event_type": "PullRequestEvent",
            "developer": "alice",
            "repository": "repo2",
            "technology_category": "Web",
            "is_defect_proxy": 0,
        },
    ])

def test_compute_hourly_activity(mock_ts_dataframe):
    hourly = compute_hourly_activity(mock_ts_dataframe, rolling_window=2)
    assert not hourly.empty
    assert len(hourly) == 3
    assert "event_count" in hourly.columns
    assert "rolling_mean" in hourly.columns
    assert "activity_velocity" in hourly.columns
    assert hourly["event_count"].sum() == 4

def test_compute_event_type_series(mock_ts_dataframe):
    res = compute_event_type_series(mock_ts_dataframe)
    assert not res.empty
    assert "PushEvent" in res.columns
    assert "IssuesEvent" in res.columns

def test_compute_category_series(mock_ts_dataframe):
    res = compute_category_series(mock_ts_dataframe)
    assert not res.empty
    assert "DevOps" in res.columns
    assert "Web" in res.columns

def test_compute_trend_summary(mock_ts_dataframe):
    hourly = compute_hourly_activity(mock_ts_dataframe)
    summary = compute_trend_summary(hourly)
    assert summary["total_events"] == 4
    assert summary["mean_hourly_events"] > 0
    assert summary["peak_hour"] is not None

def test_time_series_empty():
    empty_df = pd.DataFrame()
    assert compute_hourly_activity(empty_df).empty
    assert compute_trend_summary(pd.DataFrame())["total_events"] == 0
