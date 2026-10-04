# Software Quality Data Warehouse with Web-Mined Technology Trend Signals

A modular, production-quality Data Warehouse and Web/Text Mining platform built on a 50,000-event GitHub Archive dataset extracted via Google BigQuery. This project fulfills all requirements of the academic **Module 5: Data Warehousing and Data Mining** curriculum, implementing an end-to-end Extract-Transform-Load (ETL) pipeline, a local analytical Star Schema database, multi-dimensional OLAP queries, unsupervised text clustering, association and episode rule discovery, temporal trend decomposition, NetworkX graph mining, and a modern Streamlit analytical dashboard.

---

## 📋 Table of Contents
- [Problem Statement](#problem-statement)
- [Key Objectives](#key-objectives)
- [System Architecture](#system-architecture)
- [Data Source & Provenance](#data-source--provenance)
- [Dataset Setup](#dataset-setup)
- [Installation & Quickstart](#installation--quickstart)
- [ETL Pipeline](#etl-pipeline)
- [Data Warehouse Schema](#data-warehouse-schema)
- [Multi-Dimensional OLAP Operations](#multi-dimensional-olap-operations)
- [Web & Text Mining Methods](#web--text-mining-methods)
- [Unsupervised Text Clustering](#unsupervised-text-clustering)
- [Association & Episode Rule Discovery](#association--episode-rule-discovery)
- [Time-Series Trend Decomposition](#time-series-trend-decomposition)
- [Graph Mining & Network Analysis](#graph-mining--network-analysis)
- [Streamlit Dashboard](#streamlit-dashboard)
- [Automated Testing](#automated-testing)
- [Module 5 Syllabus Mapping](#module-5-syllabus-mapping)
- [Limitations & Future Improvements](#limitations--future-improvements)

---

## 🎯 Problem Statement

Modern software engineering telemetry generated across open-source ecosystems contains signals regarding technology adoption, developer velocity, and software defect proxies. However, raw JSON event streams are noisy, nested, unindexed, and distributed across heterogeneous event models (e.g. pushes, issue comments, pull request reviews). 

This project solves these challenges by transforming raw event data into an analytical Star Schema warehouse, enabling multidimensional slicing and dicing, and applying data mining algorithms to extract actionable technology trends and collaboration insights.

---

## 🚀 Key Objectives

1. **Robust ETL Processing**: Ingest, validate, and clean double-encoded raw GitHub Archive JSON records.
2. **Dimensional Modeling**: Construct an ANSI SQL / SQLite Star Schema with surrogate keys, foreign-key relationships, and indexing.
3. **OLAP Analytics**: Implement reusable computational functions for Roll-up, Drill-down, Slice, Dice, and Pivot operations.
4. **Web & Text Mining**: Classify technologies into category hierarchies, extract keywords using TF-IDF, and cluster issue reports.
5. **Pattern Discovery**: Mine association rules across co-occurring technologies and episode rules across event sequences.
6. **Temporal & Network Intelligence**: Decompose activity trends via moving averages and model developer-repository collaboration using bipartite graphs.
7. **Interactive Visual Dashboard**: Deliver a Streamlit + Plotly user interface with multi-dimensional filtering.

---

## 🏗️ System Architecture

```
GitHub Archive Export (50kDATASET.csv)
                  │
                  ▼
         [src/etl/extract.py]  --> Schema validation & profiling
                  │
                  ▼
        [src/etl/transform.py] --> Payload parsing, bot detection, technology taxonomy
                  │
                  ▼
          [src/etl/load.py]    --> Star schema SQLite population & Parquet caching
                  │
         ┌────────┴────────┐
         ▼                 ▼
[Analytical Warehouse]  [Mining Engine]
   - dim_time              - Text Mining (TF-IDF)
   - dim_developer         - K-Means Clustering
   - dim_repository        - Association Rules (Apriori)
   - dim_event             - Time Series Rolling Trends
   - dim_technology        - Graph Mining (NetworkX)
   - fact_github_activity
         │                 │
         └────────┬────────┘
                  ▼
      [dashboard/app.py] (Streamlit + Plotly Dashboard)
```

---

## 📊 Data Source & Provenance

The provided dataset `50kDATASET.csv` (50,000 records) is an authentic extract from the public GitHub Archive hosted on Google BigQuery (`githubarchive.day.20260901`). The dataset was retrieved using the following query:

```sql
SELECT
  id,
  created_at,
  type AS event_type,
  actor.login AS developer,
  repo.name AS repository,
  TO_JSON_STRING(payload) AS payload_json
FROM
  `githubarchive.day.20260901`
WHERE
  type IN (
    'PushEvent',
    'PullRequestEvent',
    'PullRequestReviewEvent',
    'PullRequestReviewCommentEvent',
    'IssuesEvent',
    'IssueCommentEvent',
    'ForkEvent',
    'ReleaseEvent'
  )
LIMIT 50000;
```

> **Note**: Live BigQuery credentials are **not** required for running the local project. The full 50,000-row dataset is already supplied locally.

---

## 📁 Dataset Setup

Ensure `50kDATASET.csv` is located at `data/raw/50kDATASET.csv` (or the project root). The pipeline automatically falls back to the project root if `data/raw/50kDATASET.csv` is not present.

```
data/
├── raw/
│   ├── 50kDATASET.csv
│   └── README.md
├── processed/
│   ├── processed_events.parquet
│   └── warehouse.db
└── README.md
```

---

## ⚙️ Installation & Quickstart

### 1. Prerequisites
- Python 3.11 or 3.12
- Git

### 2. Clone and Setup Environment
```bash
git clone https://github.com/swayam92/Software-Quality-Data-Warehouse-with-web-mined-Technology-Trend-Signals.git
cd Software-Quality-Data-Warehouse-with-web-mined-Technology-Trend-Signals

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Run the ETL Pipeline
Extracts, transforms, and loads the 50,000 events into the analytical database:
```bash
python -m src.etl.load
```

### 4. Run Automated Tests
```bash
pytest tests/
```

### 5. Launch the Streamlit Dashboard
```bash
streamlit run dashboard/app.py
```
Open your browser at `http://localhost:8501`.

---

## 🔄 ETL Pipeline

1. **Extract (`src/etl/extract.py`)**:
   - Locates `data/raw/50kDATASET.csv` safely.
   - Validates the required schema: `id`, `created_at`, `event_type`, `developer`, `repository`, `payload_json`.
   - Generates summary statistics on missing values, data types, and event frequency distributions.

2. **Transform (`src/etl/transform.py`)**:
   - Safely decodes double-encoded JSON payloads.
   - Converts timestamps to UTC datetime components: `date`, `hour`, `day`, `day_name`, `week`, `month`, `year`, `is_weekend`.
   - Identifies automated bots (`[bot]`, `bot-`, `jenkins`) from human developers.
   - Extracts structured issue metrics: title, comment count, labels, and defect proxy indicators (`is_defect_proxy`).
   - Classifies technologies against a deterministic taxonomy hierarchy.

3. **Load (`src/etl/load.py`)**:
   - Executes DDL script `sql/warehouse/star_schema.sql` to initialize SQLite tables.
   - Bulk-inserts dimension and fact records using chunked transactions.
   - Serializes an enriched denormalized analytical table to `data/processed/processed_events.parquet`.

---

## 🏛️ Data Warehouse Schema

### Star Schema (Implemented in `warehouse.db`)
- **`dim_time`**: Temporal surrogate keys with date, hour, day, week, month, and weekend flags.
- **`dim_developer`**: Contributor logins, bot classification, and developer types.
- **`dim_repository`**: Full repository namespaces, project names, and organization owners.
- **`dim_event`**: Event types, granular actions (`opened`, `merged`, `pushed`), and defect proxy flags.
- **`dim_technology`**: 86 derived technology signals produced by the deterministic taxonomy, with sub-categories and root category.
- **`fact_github_activity`**: Additive metrics (`activity_count`, `issue_comments_count`, `text_length`) and dimensional foreign keys.

### Snowflake Schema Alternative (Documented)
In the documented Snowflake alternative:
- `dim_technology` normalizes into `dim_technology` ➔ `dim_category` ➔ `dim_parent_category`.
- `dim_repository` normalizes into `dim_repository` ➔ `dim_owner`.
- `dim_event` normalizes into `dim_event` ➔ `dim_event_type`.

*See [docs/architecture.md](docs/architecture.md) for full ER diagrams and trade-off comparisons.*

---

## 🧊 Multi-Dimensional OLAP Operations

All five core OLAP operations are implemented as reusable functions in `src/warehouse/queries.py` and documented in `sql/warehouse/olap_queries.sql`:

1. **Roll-up**: Aggregates activity from finer temporal granularities to broader summaries (`Hour -> Day -> Week -> Month`).
2. **Drill-down**: Breaks down daily or hourly volumes into specific event types, actions, and contributors.
3. **Slice**: Isolates a 1-dimensional cross-section (e.g., filtering strictly for `event_type = 'IssuesEvent'`).
4. **Dice**: Isolates a multidimensional bounding box across multiple dimensions (e.g., `event_type IN ('PullRequestEvent', 'IssuesEvent')` AND `category IN ('DevOps', 'Web')` AND `hour BETWEEN 8 AND 14`).
5. **Pivot**: Cross-tabulates metrics into a 2D matrix (e.g., Technology Category vs. Event Type) accompanied by interactive heatmaps.

---

## 🌐 Web & Text Mining Methods

- **Web Content Mining**: Extracts and cleans unstructured natural-language text from issue titles, review comments, and issue labels, evaluating lexical features via Term Frequency-Inverse Document Frequency (TF-IDF).
- **Web Structure Mining**: Formulates bipartite graph networks linking Developers ↔ Repositories and Repositories ↔ Technologies using NetworkX, evaluating topological centrality, density, and connected components.
- **Platform Activity Telemetry vs. Traditional Clickstream Usage Mining**:
  > **Crucial Academic & Viva Distinction**: Traditional Web Usage Mining analyzes HTTP server access logs and browser clickstream data (page requests, navigation trails, dwell times). GitHub Archive does **not** contain browser navigation or clickstream data. Instead, the usage analysis in this project evaluates **GitHub platform activity telemetry**—modeling developer interactions across the software development lifecycle (commits, code reviews, issue discussions, releases) and activity velocity over time.
- **Category Taxonomy Hierarchy**: Deterministically maps extracted keywords into **86 derived technology signals** across 7 structured branches:
  ```
  Software
  ├── Development (Rust, Go, C++, Java, GraphQL, REST, Git)
  ├── Web (React, Vue, Svelte, Next.js, TypeScript, Django, FastAPI)
  ├── DevOps (Docker, Kubernetes, Terraform, Ansible, GitHub Actions)
  ├── Databases (PostgreSQL, MySQL, MongoDB, Redis, OpenSearch)
  ├── Infrastructure (AWS, Azure, GCP, Linux, Serverless, NGINX)
  ├── Mobile (Android, iOS, Swift, Kotlin, Flutter, React Native)
  └── Data (Python, Pandas, Spark, Kafka, PyTorch, Machine Learning)
  ```

---

## 🧩 Unsupervised Text Clustering

Implemented in `src/mining/clustering.py` using **TF-IDF Vectorization** + **K-Means Clustering**:
- Discovers latent topic groupings among issue reports and developer commentary.
- Calculates **Silhouette Coefficients** to assess cluster cohesion and separation.
- Built-in defensive fallback safely handles empty inputs, single documents, or insufficient sample counts without crashing.

---

## 🔗 Association & Episode Rule Discovery

Implemented in `src/mining/association_rules.py` using an Apriori-style frequent itemset mining algorithm:
- **Technology Co-occurrences**: Evaluates frequent technology pairings within repositories (e.g., `flutter` ➔ `git`, `docker` ➔ `kubernetes`).
- **Event Episodes**: Evaluates sequences of events (e.g., `PushEvent` + `PullRequestEvent` ➔ `IssueCommentEvent`).
- Computes statistical metrics:
  $$\text{Support} = P(A \cup B), \quad \text{Confidence} = \frac{P(A \cup B)}{P(A)}, \quad \text{Lift} = \frac{\text{Confidence}}{P(B)}$$

---

## 📈 Time-Series Trend Decomposition

Implemented in `src/mining/time_series.py`:
- Aggregates activity counts into uniform hourly buckets.
- Calculates **3-period moving averages** and **rolling standard deviations** to isolate trend trajectories.
- Evaluates **Activity Velocity** ($\Delta \text{events} / \Delta t$) to detect telemetry acceleration and peak operating windows.

---

## 🕸️ Graph Mining & Network Analysis

Implemented in `src/mining/graph_mining.py` with **NetworkX**:
- Constructs bipartite collaboration networks linking **Developers ↔ Repositories** and **Repositories ↔ Technologies**.
- Edge weights represent interaction frequencies.
- Evaluates topological graph metrics: **Degree Centrality**, **Weighted Degree**, **Graph Density**, and **Connected Components**.

---

## 🖥️ Streamlit Dashboard

The Streamlit dashboard (`dashboard/app.py`) provides an interactive interface with 9 analytical views:

1. **🏛️ Summary & KPIs**: High-level telemetry, active developer/repository metrics, event breakdowns, and top contributors.
2. **🧊 OLAP Cube**: Interactive interface for Roll-up, Drill-down, Slice, Dice, and Pivot heatmaps.
3. **🛡️ Quality & Defects**: Defect proxy distributions, issue discussion depth, and repository risk rankings.
4. **🌐 Web & Text Mining**: Interactive category sunburst diagram and top TF-IDF keyword charts.
5. **🧩 Clustering**: Interactive K-Means cluster configuration, silhouette scores, and cluster keyword inspections.
6. **🔗 Association Rules**: Support/confidence sliders, rule tables, and support vs. confidence scatter plots.
7. **📈 Time Series**: Moving average trendlines, hourly velocity, and event composition area charts.
8. **🕸️ Graph Mining**: Network metrics, centrality leaderboards, and node tables.
9. **💾 Schema & Export**: CSV filtered dataset export and Star vs. Snowflake schema comparisons.

---

## 🧪 Automated Testing

A comprehensive test suite is implemented under `tests/` covering all pipeline modules:

| Test Module | Coverage Focus |
| :--- | :--- |
| `tests/test_etl.py` | Column validation, JSON decoding, duplicate resolution, transformation |
| `tests/test_warehouse.py` | SQLite DDL initialization, foreign keys, row counts, table loading |
| `tests/test_olap.py` | Roll-up, Drill-down, Slice, Dice, and Pivot execution |
| `tests/test_mining.py` | Text cleaning, TF-IDF, K-Means clustering edge cases, Association rules |
| `tests/test_time_series.py`| Hourly resampling, rolling statistics, velocity, empty handling |
| `tests/test_graph.py` | Bipartite graph creation, network metrics, node table extraction |

Run the entire test suite with:
```bash
pytest tests/
```

---

## 🎓 Module 5 Syllabus Mapping

| Syllabus Topic | Project Implementation & Proof of Concept |
| :--- | :--- |
| **Data Warehouse & OLTP vs OLAP** | Detailed architectural comparison documented in `docs/architecture.md`; Star Schema database implemented in `warehouse.db`. |
| **ETL Process & Tools** | End-to-end Python, Pandas, and SQLAlchemy pipeline in `src/etl/extract.py`, `transform.py`, and `load.py`. |
| **Star & Snowflake Schemas** | Star schema implemented in `sql/warehouse/star_schema.sql`; Snowflake alternative documented in `docs/architecture.md`. |
| **OLAP Operations** | Reusable Roll-up, Drill-down, Slice, Dice, and Pivot functions in `src/warehouse/queries.py` and `sql/warehouse/olap_queries.sql`. |
| **Reporting & Dashboards** | Interactive multi-view Streamlit + Plotly analytical application in `dashboard/app.py`. |
| **Web Content Mining** | Extraction, tokenization, and TF-IDF analysis of unstructured issue text in `src/mining/text_mining.py`. |
| **Web Structure Mining** | Bipartite Developer-Repository graph analysis and centrality metrics in `src/mining/graph_mining.py`. |
| **Web Usage Mining** | GitHub platform activity telemetry (commits, code reviews, issue discussions). Note: GH Archive does not contain browser clickstream/navigation logs; this analysis models platform activity telemetry rather than traditional web clickstream mining. |
| **Text Clustering** | Unsupervised K-Means clustering on TF-IDF feature matrices with silhouette scoring in `src/mining/clustering.py`. |
| **Association & Episode Rules** | Apriori-style mining of technology co-occurrences and event sequences in `src/mining/association_rules.py`. |
| **Hierarchy of Categories** | Deterministic technology taxonomy tree mapping 86 derived technology signals across 7 categories in `src/utils/config.py`. |
| **Time Series Analysis** | Hourly resampling, moving averages, velocity, and trend summaries in `src/mining/time_series.py`. |
| **Graph Mining** | Node degree, weighted degree, connected components, and density metrics using NetworkX. |

---

## ⚠️ Limitations & Future Improvements

1. **Temporal Horizon**: The provided 50K export represents an intensive single-day snapshot (`2026-09-01`). Future work includes appending multi-month or annual partitions to enable seasonality and cyclical forecasting.
2. **External Data Sources**: The modular architecture supports plug-and-play ingestion of Stack Exchange or CVE vulnerability databases to correlate defect proxies with public questions and security advisories.
3. **Distributed Execution**: For multi-gigabyte or terabyte archives, the pandas and SQLite processing logic can scale seamlessly to PySpark or DuckDB.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.