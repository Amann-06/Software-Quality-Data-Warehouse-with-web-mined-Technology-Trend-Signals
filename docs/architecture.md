# Software Quality Data Warehouse & Web Mining Architecture

This document outlines the architectural blueprint, data warehouse designs, mining workflows, and theoretical syllabus mappings for the Software Quality Data Warehouse with Web-Mined Technology Trend Signals project.

---

## 1. System Architecture Overview

The system processes large-scale software engineering telemetry extracted from Google BigQuery's GitHub Archive export (`50kDATASET.csv`). It follows a decoupled, reproducible pipeline:

```
+---------------------------------------------------------------------------------+
|                                DATA SOURCE                                      |
|  GitHub Archive Telemetry via Google BigQuery (`githubarchive.day.20260901`)   |
+---------------------------------------------------------------------------------+
                                      │
                                      ▼
+---------------------------------------------------------------------------------+
|                             ETL SUBSYSTEM (src/etl)                             |
|  1. Extract: Column validation, structural profiling, missing value auditing    |
|  2. Transform: Double-encoded JSON parsing, timestamp UTC normalization,        |
|                Bot classification, technology taxonomy matching, defect proxying|
|  3. Load: Star schema loading into SQLite (`warehouse.db`), Parquet caching     |
+---------------------------------------------------------------------------------+
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
+-----------------------------------+     +-----------------------------------+
|     ANALYTICAL DATA WAREHOUSE     |     |       DATA MINING ENGINE          |
|         (src/warehouse)           |     |          (src/mining)             |
|  - Star Schema (5 Dims + 1 Fact)  |     |  - Web / Text Content Mining      |
|  - Documented Snowflake Schema    |     |  - TF-IDF & Keyword Extraction    |
|  - OLAP Operations:               |     |  - K-Means Text Clustering        |
|    * Roll-up (Hierarchical agg)   |     |  - Association & Episode Rules    |
|    * Drill-down (Decomposition)   |     |  - Time Series Rolling Trends     |
|    * Slice (1D boundary filter)   |     |  - NetworkX Graph Mining          |
|    * Dice (Multi-D constraint)    |     +-----------------------------------+
|    * Pivot (2D Cross-tabulation)  |                       │
+-----------------------------------+                       │
                 │                                          │
                 └────────────────────┬─────────────────────┘
                                      ▼
+---------------------------------------------------------------------------------+
|                       INTERACTIVE STREAMLIT DASHBOARD                           |
|  - Dynamic filter panel (Category, Event, Developer Type, Hourly Window)        |
|  - KPI metric cards, Plotly charts, OLAP query explorers, Graph visualizer      |
+---------------------------------------------------------------------------------+
```

---

## 2. OLTP vs. OLAP Paradigm Comparison

| Dimension | OLTP (Online Transaction Processing) | OLAP (Online Analytical Processing) | This Project's Implementation |
| :--- | :--- | :--- | :--- |
| **System Objective** | Operational day-to-day transactions | Analytical decision-making & pattern discovery | Analytical reporting on developer and quality dynamics |
| **Data Nature** | Current, granular, highly mutable | Historical, point-in-time snapshot, read-only | Immutable 50K event snapshot partitioned into star tables |
| **Database Design** | Highly normalized (3NF / BCNF) to eliminate anomalies | Denormalized multidimensional Star or Snowflake schema | Star schema optimized for OLAP aggregations |
| **Access Patterns** | Frequent atomic read/writes of individual rows | Complex queries joining dimensions over millions of rows | Reusable multi-dimensional roll-up, drill-down, slice, dice, pivot |
| **Indexing Focus** | Primary keys for rapid single-row lookup | Foreign keys and dimensional hierarchies for group-by speed | Indexed surrogate keys on all dimensions and fact columns |

---

## 3. Data Warehouse Schema Architectures

### A. Implemented Star Schema

The star schema organizes data into a central fact table surrounded by non-redundant, denormalized dimension tables. The `dim_technology` dimension captures 86 derived technology signals produced by the deterministic taxonomy across 7 high-level categories (Software ➔ Web, DevOps, Infrastructure, Databases, Data, Mobile, Development).

```
       +-----------------------+
       |       dim_time        |
       +-----------------------+
       | PK  time_key          |
       |     created_at        |
       |     date              |
       |     hour              |
       |     day, week, month  |
       |     is_weekend        |
       +-----------------------+
                   │
                   │ 1:N
                   ▼
+---------------------+       +-----------------------+       +---------------------+
|    dim_developer    |       |  fact_github_activity |       |    dim_repository   |
+---------------------+       +-----------------------+       +---------------------+
| PK  developer_key   |◄─────┤ PK  fact_id           ├─────►| PK  repository_key  |
|     developer_login |  N:1  |     event_id          |  1:N  |     full_name       |
|     is_bot          |       | FK  time_key          |       |     owner           |
|     developer_type  |       | FK  developer_key     |       |     repo_name       |
+---------------------+       | FK  repository_key    |       +---------------------+
                              | FK  event_key         |
                              | FK  technology_key    |
                              |     activity_count    |
                              |     issue_comments    |
                              |     text_length       |
                              |     has_issue_flag    |
                              |     has_pr_flag       |
                              +-----------------------+
                                  ▲               ▲
                              N:1 │               │ N:1
       +--------------------------+               +--------------------------+
       |        dim_event         |               |      dim_technology      |
       +--------------------------+               +--------------------------+
       | PK  event_key            |               | PK  technology_key       |
       |     event_type           |               |     technology_name      |
       |     action               |               |     category             |
       |     is_defect_proxy      |               |     parent_category      |
       |     is_review_event      |               +--------------------------+
       +--------------------------+
```

### B. Documented Snowflake Schema Alternative

In a Snowflake schema, dimension tables are normalized to 3NF, creating dimension hierarchies:

1. **Technology Dimension Normalization**:
   - `fact_github_activity` -> `dim_technology` (stores `technology_key`, `technology_name`, `category_id`)
   - `dim_category` (stores `category_id`, `category_name`, `parent_id`)
   - `dim_parent_category` (stores `parent_id`, `parent_name`)
2. **Repository Dimension Normalization**:
   - `fact_github_activity` -> `dim_repository` (stores `repository_key`, `repo_name`, `owner_id`)
   - `dim_owner` (stores `owner_id`, `owner_login`, `owner_type`)
3. **Event Dimension Normalization**:
   - `fact_github_activity` -> `dim_event` (stores `event_key`, `action_id`, `type_id`)
   - `dim_event_type` (stores `type_id`, `type_name`, `is_defect_proxy`)
   - `dim_action` (stores `action_id`, `action_name`)

**Trade-off Analysis:**
- **Star Schema Benefit**: Lower query execution latency in analytical databases like SQLite or DuckDB due to fewer join hops.
- **Snowflake Schema Benefit**: Reduced attribute redundancy and strict referential integrity for complex taxonomy updates.

---

## 4. Multi-Dimensional OLAP Operations

1. **Roll-up**: Aggregates metric measures moving up the dimension hierarchy (`Hour -> Day -> Week -> Month`). Implemented in SQL using multi-level `GROUP BY`.
2. **Drill-down**: Decomposes aggregated measures into finer granularities (e.g., inspecting a specific calendar hour down to individual event actions and contributors).
3. **Slice**: Performs a 1-dimensional cross-section by fixing a single dimension attribute (e.g., `event_type = 'IssuesEvent'`).
4. **Dice**: Isolates a sub-cube by constraining multiple dimensions simultaneously (e.g., `event_type IN ('PullRequestEvent', 'IssuesEvent')` AND `category IN ('DevOps', 'Web')` AND `hour BETWEEN 8 AND 14`).
5. **Pivot**: Rotates the multidimensional data axes to present a 2-way cross-tabulation matrix (e.g., Technology Category vs. Event Type).

---

## 5. Web and Data Mining Methodology

### A. Web Content Mining
- Parses natural-language unstructured fields from event payloads: issue titles, discussion comment bodies, and release release notes.
- Extracts lexical features and calculates Term Frequency-Inverse Document Frequency (TF-IDF) vectors using scikit-learn.
- Filters out non-informative English stop words and computes average TF-IDF scores across categories.

### B. Web Structure & Graph Mining
- Formulates bipartite collaboration networks using NetworkX:
  - **Developer ↔ Repository Network**: Nodes are contributors and repositories; edge weights reflect total committed events.
  - **Repository ↔ Technology Network**: Nodes are software repositories and extracted technology tags.
- Calculates network metrics: Node degree, weighted degree, graph density, connected components, and degree centrality.

### C. Platform Activity Telemetry vs. Traditional Web Clickstream Mining
- **Critical Academic & Viva Distinction**: Traditional Web Usage Mining relies on Web server access logs, session tokens, and HTTP browser clickstream data (page requests, hyperlinks clicked, dwell times, and navigation paths).
- **GitHub Archive Scope**: GitHub Archive does **not** contain browser navigation, page-view, or clickstream logs.
- **Implemented Usage Analysis**: The usage analysis in this project is implemented as **GitHub platform activity telemetry**—capturing developer actions across the software development lifecycle (code commits, pull request submissions, code review approvals, issue discussions, and releases). This models collaborative developer workflows and temporal interaction velocity rather than browser navigation sessions.

### D. Unsupervised Clustering
- Implements K-Means clustering over normalized TF-IDF feature matrices.
- Discovers latent topic groupings among issue reports and developer commentary.
- Calculates Silhouette Coefficients to measure intra-cluster cohesion and inter-cluster separation.
- Integrates graceful fallback handling for small or edge-case corpora.

### E. Association & Episode Rule Discovery
- Employs Apriori-style frequent itemset mining on co-occurring technology stacks and sequential event types within repositories.
- Evaluates statistical significance metrics:
  $$\text{Support}(A \rightarrow B) = P(A \cup B)$$
  $$\text{Confidence}(A \rightarrow B) = \frac{P(A \cup B)}{P(A)}$$
  $$\text{Lift}(A \rightarrow B) = \frac{\text{Confidence}(A \rightarrow B)}{P(B)}$$
- Identifies strong technology pairings (e.g., `flutter` + `git`, `docker` + `kubernetes`).

### F. Time Series Trend Decomposition
- Resamples event velocity by hourly temporal buckets.
- Computes 3-period and 6-period moving averages to smooth short-term telemetry bursts.
- Calculates activity velocity (rate of change between consecutive periods) and isolates peak activity windows.
