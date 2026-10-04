# Data Dictionary

Comprehensive documentation for all raw source fields, derived features, and warehouse dimensional models.

---

## 1. Raw Source Dataset (`50kDATASET.csv`)

Obtained via Google BigQuery export from the public `githubarchive.day.20260901` table.

| Column Name | Data Type | Nullable | Description | Sample Value |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `int64` | No | Unique 64-bit integer identifier for the GitHub Archive event | `19645497524` |
| `created_at` | `string` | No | ISO-8601 UTC timestamp string of event generation | `2026-09-01 09:04:13 UTC` |
| `event_type` | `string` | No | GitHub Archive event classification string | `PushEvent`, `IssuesEvent` |
| `developer` | `string` | No | GitHub username / actor login handle of the contributor | `abhiyerra`, `dependabot[bot]` |
| `repository` | `string` | No | Full repository namespace in `owner/repo_name` format | `opszero/terraform-aws-instance` |
| `payload_json` | `string` | No | Serialized JSON string containing event-specific telemetry | `{"ref": "refs/heads/main", ...}` |

---

## 2. Derived and Analytical Features

Constructed during the ETL transformation stage (`src/etl/transform.py`).

| Feature Name | Target Type | Derivation Logic | Analytical Purpose |
| :--- | :--- | :--- | :--- |
| `created_at_dt` | `datetime64[ns, UTC]` | Parsed from `created_at` | Time series indexation and rolling calculations |
| `date` | `string` (YYYY-MM-DD) | Extracted date component | Daily partitioning and drill-down |
| `hour` | `int64` (0–23) | Extracted hourly component | Hourly activity velocity and peak analysis |
| `is_weekend` | `int64` (0 or 1) | True if day of week is Saturday or Sunday | Workday vs. weekend developer behavior |
| `is_bot` | `int64` (0 or 1) | Detected if login contains `[bot]`, `bot-`, or `jenkins` | Human vs. automation activity segmentation |
| `repo_owner` | `string` | First segment of `repository.split('/')` | Organizational grouping |
| `repo_name` | `string` | Second segment of `repository.split('/')` | Project-level isolation |
| `action` | `string` | Extracted from payload `action` key | Finer granularity event action (e.g. `opened`, `merged`) |
| `issue_title` | `string` | Extracted from `payload.issue.title` | Natural language text mining and clustering |
| `comment_body` | `string` | Extracted from `payload.comment.body` | Unstructured developer commentary text |
| `issue_labels` | `string` | Space-separated list of issue label names | Defect classification (`bug`, `p1`, `defect`) |
| `issue_comments_count`| `int64` | Extracted from `payload.issue.comments` | Issue complexity / discussion depth proxy |
| `is_defect_proxy` | `int64` (0 or 1) | 1 for issue events or bug/defect label flags | Software quality / defect rate proxy metric |
| `has_issue_flag` | `int64` (0 or 1) | 1 if event relates to an issue | Issue tracking filter |
| `has_pr_flag` | `int64` (0 or 1) | 1 if event relates to a pull request | Code review tracking filter |
| `primary_technology` | `string` | Deterministic taxonomy match from repo and text | Technological footprint assignment |
| `technology_category` | `string` | Mapped parent category (`Web`, `DevOps`, etc.) | High-level categorization |
| `technologies` | `string` | Semicolon-separated list of all matched technologies | Transaction itemset generation for association rules |
| `extracted_text` | `string` | Concatenation of repo, issue title, and labels | Corpus input for TF-IDF and KMeans |

---

## 3. Data Warehouse Star Schema Tables (`warehouse.db`)

### `dim_time`
Temporal dimension table supporting hierarchical roll-ups and drill-downs.

| Column | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `time_key` | `INTEGER` | `PRIMARY KEY` | Surrogate time dimension key |
| `created_at` | `TEXT` | `NOT NULL` | Raw UTC timestamp string |
| `date` | `TEXT` | `NOT NULL` | Date string (YYYY-MM-DD) |
| `hour` | `INTEGER` | `NOT NULL` | Hour of the day (0–23) |
| `day` | `INTEGER` | `NOT NULL` | Day of the month (1–31) |
| `day_name` | `TEXT` | `NOT NULL` | Calendar day name (Monday–Sunday) |
| `week` | `INTEGER` | `NOT NULL` | ISO calendar week number |
| `month` | `INTEGER` | `NOT NULL` | Calendar month (1–12) |
| `year` | `INTEGER` | `NOT NULL` | Calendar year |
| `is_weekend` | `INTEGER` | `NOT NULL` | Binary indicator for weekend |

### `dim_developer`
Actor dimension capturing individual contributors and automated bots.

| Column | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `developer_key` | `INTEGER` | `PRIMARY KEY` | Surrogate developer key |
| `developer_login` | `TEXT` | `NOT NULL UNIQUE` | GitHub login handle |
| `is_bot` | `INTEGER` | `NOT NULL` | Binary bot flag |
| `developer_type` | `TEXT` | `NOT NULL` | Type classification (`user` or `bot`) |

### `dim_repository`
Software repository dimension capturing ownership and naming.

| Column | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `repository_key` | `INTEGER` | `PRIMARY KEY` | Surrogate repository key |
| `full_name` | `TEXT` | `NOT NULL UNIQUE` | Full repo identifier (`owner/repo`) |
| `owner` | `TEXT` | `NOT NULL` | Account or organization owner |
| `repo_name` | `TEXT` | `NOT NULL` | Repository name |

### `dim_event`
Event type and action classification dimension.

| Column | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `event_key` | `INTEGER` | `PRIMARY KEY` | Surrogate event key |
| `event_type` | `TEXT` | `NOT NULL` | Event category (`PushEvent`, etc.) |
| `action` | `TEXT` | `NOT NULL` | Specific event action (`opened`, `pushed`) |
| `is_defect_proxy` | `INTEGER` | `NOT NULL` | Quality proxy flag |
| `is_review_event` | `INTEGER` | `NOT NULL` | Code review proxy flag |

### `dim_technology`
Taxonomy dimension classifying 86 derived technology signals produced by the deterministic taxonomy across categories.

| Column | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `technology_key` | `INTEGER` | `PRIMARY KEY` | Surrogate technology key |
| `technology_name` | `TEXT` | `NOT NULL` | Matched technology name (`react`, `docker`) |
| `category` | `TEXT` | `NOT NULL` | Sub-category (`Web`, `DevOps`, `Data`) |
| `parent_category` | `TEXT` | `NOT NULL` | Top-level root category (`Software`) |

### `fact_github_activity`
Central fact table recording atomic software engineering activities.

| Column | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `fact_id` | `INTEGER` | `PRIMARY KEY` | Unique surrogate fact record ID |
| `event_id` | `INTEGER` | `NOT NULL` | Degenerate dimension (original event ID) |
| `time_key` | `INTEGER` | `FK -> dim_time` | Foreign key referencing `dim_time` |
| `developer_key` | `INTEGER` | `FK -> dim_developer` | Foreign key referencing `dim_developer` |
| `repository_key` | `INTEGER` | `FK -> dim_repository`| Foreign key referencing `dim_repository` |
| `event_key` | `INTEGER` | `FK -> dim_event` | Foreign key referencing `dim_event` |
| `technology_key` | `INTEGER` | `FK -> dim_technology`| Foreign key referencing `dim_technology` |
| `activity_count` | `INTEGER` | `NOT NULL` | Additive metric count (default 1) |
| `issue_comments_count`| `INTEGER` | `NOT NULL` | Additive metric for discussion comments |
| `text_length` | `INTEGER` | `NOT NULL` | Additive metric for unstructured text bytes |
| `has_issue_flag` | `INTEGER` | `NOT NULL` | Binary indicator for issue events |
| `has_pr_flag` | `INTEGER` | `NOT NULL` | Binary indicator for pull request events |
