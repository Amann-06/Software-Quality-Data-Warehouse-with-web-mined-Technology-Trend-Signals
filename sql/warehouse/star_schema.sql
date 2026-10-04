-- Star Schema DDL for GitHub Quality & Activity Data Warehouse
-- Local Engine: SQLite / ANSI SQL compatible

DROP TABLE IF EXISTS fact_github_activity;
DROP TABLE IF EXISTS dim_time;
DROP TABLE IF EXISTS dim_developer;
DROP TABLE IF EXISTS dim_repository;
DROP TABLE IF EXISTS dim_event;
DROP TABLE IF EXISTS dim_technology;

CREATE TABLE dim_time (
    time_key INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    week INTEGER NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE dim_developer (
    developer_key INTEGER PRIMARY KEY,
    developer_login TEXT NOT NULL UNIQUE,
    is_bot INTEGER NOT NULL DEFAULT 0,
    developer_type TEXT NOT NULL
);

CREATE TABLE dim_repository (
    repository_key INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL UNIQUE,
    owner TEXT NOT NULL,
    repo_name TEXT NOT NULL
);

CREATE TABLE dim_event (
    event_key INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    action TEXT NOT NULL,
    is_defect_proxy INTEGER NOT NULL DEFAULT 0,
    is_review_event INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE dim_technology (
    technology_key INTEGER PRIMARY KEY,
    technology_name TEXT NOT NULL,
    category TEXT NOT NULL,
    parent_category TEXT NOT NULL DEFAULT 'Software'
);

CREATE TABLE fact_github_activity (
    fact_id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    time_key INTEGER NOT NULL,
    developer_key INTEGER NOT NULL,
    repository_key INTEGER NOT NULL,
    event_key INTEGER NOT NULL,
    technology_key INTEGER NOT NULL,
    activity_count INTEGER NOT NULL DEFAULT 1,
    issue_comments_count INTEGER NOT NULL DEFAULT 0,
    text_length INTEGER NOT NULL DEFAULT 0,
    has_issue_flag INTEGER NOT NULL DEFAULT 0,
    has_pr_flag INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (time_key) REFERENCES dim_time(time_key),
    FOREIGN KEY (developer_key) REFERENCES dim_developer(developer_key),
    FOREIGN KEY (repository_key) REFERENCES dim_repository(repository_key),
    FOREIGN KEY (event_key) REFERENCES dim_event(event_key),
    FOREIGN KEY (technology_key) REFERENCES dim_technology(technology_key)
);

CREATE INDEX idx_fact_time ON fact_github_activity(time_key);
CREATE INDEX idx_fact_dev ON fact_github_activity(developer_key);
CREATE INDEX idx_fact_repo ON fact_github_activity(repository_key);
CREATE INDEX idx_fact_event ON fact_github_activity(event_key);
CREATE INDEX idx_fact_tech ON fact_github_activity(technology_key);
CREATE INDEX idx_time_date_hour ON dim_time(date, hour);
