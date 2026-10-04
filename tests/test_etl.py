import json
import pytest
import pandas as pd
from pathlib import Path

from src.etl.extract import validate_columns, summarize_extraction, extract_data
from src.etl.transform import (
    parse_payload,
    clean_and_normalize,
    extract_payload_features,
    transform_data,
    detect_technologies,
)

@pytest.fixture
def sample_raw_dataframe():
    return pd.DataFrame([
        {
            "id": 1001,
            "created_at": "2026-09-01 10:00:00 UTC",
            "event_type": "PushEvent",
            "developer": "alice",
            "repository": "alice/docker-python-app",
            "payload_json": json.dumps({"ref": "refs/heads/main", "commits": [{"message": "Initial commit"}]}),
        },
        {
            "id": 1002,
            "created_at": "2026-09-01 11:30:00 UTC",
            "event_type": "IssuesEvent",
            "developer": "bob",
            "repository": "alice/docker-python-app",
            "payload_json": json.dumps({"action": "opened", "issue": {"title": "Fix memory bug", "labels": [{"name": "bug"}], "comments": 2}}),
        },
        {
            "id": 1003,
            "created_at": "2026-09-01 12:00:00 UTC",
            "event_type": "PullRequestEvent",
            "developer": "charlie[bot]",
            "repository": "org/react-dashboard",
            "payload_json": json.dumps({"action": "merged", "pull_request": {"title": "Update React UI", "state": "closed"}}),
        },
    ])

def test_validate_columns_success(sample_raw_dataframe):
    validate_columns(sample_raw_dataframe)

def test_validate_columns_missing():
    invalid_df = pd.DataFrame([{"id": 1, "created_at": "2026-09-01"}])
    with pytest.raises(ValueError, match="missing required columns"):
        validate_columns(invalid_df)

def test_summarize_extraction(sample_raw_dataframe):
    stats = summarize_extraction(sample_raw_dataframe)
    assert stats["row_count"] == 3
    assert stats["column_count"] == 6
    assert "PushEvent" in stats["event_distribution"]

def test_parse_payload_variations():
    assert parse_payload(None) == {}
    assert parse_payload("") == {}
    assert parse_payload('{"key": "val"}') == {"key": "val"}
    # Double-encoded JSON string
    double_encoded = json.dumps(json.dumps({"nested": 123}))
    assert parse_payload(double_encoded) == {"nested": 123}
    assert parse_payload("malformed json {") == {}

def test_clean_and_normalize_duplicates():
    dup_df = pd.DataFrame([
        {
            "id": 1,
            "created_at": "2026-09-01 10:00:00 UTC",
            "event_type": "PushEvent",
            "developer": "dev1",
            "repository": "org/repo1",
            "payload_json": "{}",
        },
        {
            "id": 1,
            "created_at": "2026-09-01 10:00:00 UTC",
            "event_type": "PushEvent",
            "developer": "dev1",
            "repository": "org/repo1",
            "payload_json": "{}",
        },
    ])
    cleaned = clean_and_normalize(dup_df)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["repo_owner"] == "org"
    assert cleaned.iloc[0]["repo_name"] == "repo1"

def test_detect_technologies():
    matches = detect_technologies("alice/docker-python-app")
    tech_names = [m[0] for m in matches]
    assert "docker" in tech_names
    assert "python" in tech_names

def test_transform_data_structure(sample_raw_dataframe):
    enriched, tables = transform_data(sample_raw_dataframe)
    assert len(enriched) == 3
    assert "dim_time" in tables
    assert "dim_developer" in tables
    assert "dim_repository" in tables
    assert "dim_event" in tables
    assert "dim_technology" in tables
    assert "fact_github_activity" in tables
    assert len(tables["fact_github_activity"]) == 3

def test_defect_proxy_discrimination():
    df = pd.DataFrame([
        {
            "id": 501,
            "created_at": "2026-09-01 10:00:00 UTC",
            "event_type": "IssuesEvent",
            "developer": "dev1",
            "repository": "org/repo",
            "payload_json": json.dumps({"action": "opened", "issue": {"title": "Critical memory leak crash in worker", "labels": [{"name": "bug"}]}}),
        },
        {
            "id": 502,
            "created_at": "2026-09-01 10:05:00 UTC",
            "event_type": "IssuesEvent",
            "developer": "dev2",
            "repository": "org/repo",
            "payload_json": json.dumps({"action": "opened", "issue": {"title": "Update README documentation guide", "labels": [{"name": "docs"}]}}),
        },
    ])
    enriched, _ = transform_data(df)
    assert enriched.loc[enriched["id"] == 501, "is_defect_proxy"].values[0] == 1
    assert enriched.loc[enriched["id"] == 502, "is_defect_proxy"].values[0] == 0

def test_technology_taxonomy_deterministic():
    matches_web = detect_technologies("org/react-nextjs-frontend")
    matches_devops = detect_technologies("infra/terraform-aws-kubernetes")
    tech_web = [m[0] for m in matches_web]
    tech_devops = [m[0] for m in matches_devops]

    assert "react" in tech_web
    assert "terraform" in tech_devops
    assert "kubernetes" in tech_devops
