from typing import Optional, List, Tuple
import pandas as pd
from sqlalchemy import Engine, text

from src.warehouse.schema import get_engine

def olap_rollup(engine: Optional[Engine] = None, group_by: str = "hour") -> pd.DataFrame:
    eng = engine or get_engine()
    group_cols = {
        "month": ["t.month"],
        "week": ["t.month", "t.week"],
        "day": ["t.month", "t.week", "t.day", "t.date"],
        "hour": ["t.date", "t.hour"],
    }
    cols = group_cols.get(group_by.lower(), ["t.date", "t.hour"])
    group_clause = ", ".join(cols)

    query = f"""
    SELECT
        {group_clause},
        COUNT(f.fact_id) AS total_events,
        SUM(e.is_defect_proxy) AS defect_proxies,
        COUNT(DISTINCT f.repository_key) AS unique_repositories,
        COUNT(DISTINCT f.developer_key) AS unique_developers
    FROM fact_github_activity f
    JOIN dim_time t ON f.time_key = t.time_key
    JOIN dim_event e ON f.event_key = e.event_key
    GROUP BY {group_clause}
    ORDER BY {group_clause}
    """
    with eng.connect() as conn:
        return pd.read_sql(text(query), conn)

def olap_drilldown(
    engine: Optional[Engine] = None,
    target_date: Optional[str] = None,
    target_hour: Optional[int] = None
) -> pd.DataFrame:
    eng = engine or get_engine()
    where_clauses = []
    if target_date:
        where_clauses.append(f"t.date = '{target_date}'")
    if target_hour is not None:
        where_clauses.append(f"t.hour = {target_hour}")

    where_stmt = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT
        t.date,
        t.hour,
        e.event_type,
        e.action,
        tech.category,
        COUNT(f.fact_id) AS event_count,
        COUNT(DISTINCT f.developer_key) AS unique_developers
    FROM fact_github_activity f
    JOIN dim_time t ON f.time_key = t.time_key
    JOIN dim_event e ON f.event_key = e.event_key
    JOIN dim_technology tech ON f.technology_key = tech.technology_key
    {where_stmt}
    GROUP BY t.date, t.hour, e.event_type, e.action, tech.category
    ORDER BY t.date, t.hour, event_count DESC
    """
    with eng.connect() as conn:
        return pd.read_sql(text(query), conn)

def olap_slice(
    engine: Optional[Engine] = None,
    dimension: str = "event_type",
    value: str = "PushEvent"
) -> pd.DataFrame:
    eng = engine or get_engine()
    dim_map = {
        "event_type": "e.event_type",
        "repository": "r.full_name",
        "developer": "d.developer_login",
        "category": "tech.category",
        "technology": "tech.technology_name",
    }
    dim_col = dim_map.get(dimension.lower(), "e.event_type")

    query = f"""
    SELECT
        r.full_name AS repository,
        tech.category,
        e.event_type,
        COUNT(f.fact_id) AS activity_count,
        SUM(f.issue_comments_count) AS total_comments,
        COUNT(DISTINCT f.developer_key) AS unique_developers
    FROM fact_github_activity f
    JOIN dim_time t ON f.time_key = t.time_key
    JOIN dim_developer d ON f.developer_key = d.developer_key
    JOIN dim_repository r ON f.repository_key = r.repository_key
    JOIN dim_event e ON f.event_key = e.event_key
    JOIN dim_technology tech ON f.technology_key = tech.technology_key
    WHERE {dim_col} = :val
    GROUP BY r.full_name, tech.category, e.event_type
    ORDER BY activity_count DESC
    LIMIT 100
    """
    with eng.connect() as conn:
        return pd.read_sql(text(query), conn, params={"val": value})

def olap_dice(
    engine: Optional[Engine] = None,
    event_types: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    hour_range: Optional[Tuple[int, int]] = None,
    developer_type: Optional[str] = None
) -> pd.DataFrame:
    eng = engine or get_engine()
    filters = []

    if event_types:
        quoted = ", ".join([f"'{e}'" for e in event_types])
        filters.append(f"e.event_type IN ({quoted})")
    if categories:
        quoted = ", ".join([f"'{c}'" for c in categories])
        filters.append(f"tech.category IN ({quoted})")
    if hour_range:
        filters.append(f"t.hour BETWEEN {hour_range[0]} AND {hour_range[1]}")
    if developer_type:
        filters.append(f"d.developer_type = '{developer_type}'")

    where_stmt = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
    SELECT
        t.hour,
        e.event_type,
        tech.category,
        d.developer_type,
        COUNT(f.fact_id) AS event_count,
        COUNT(DISTINCT f.repository_key) AS unique_repos,
        COUNT(DISTINCT f.developer_key) AS unique_devs
    FROM fact_github_activity f
    JOIN dim_time t ON f.time_key = t.time_key
    JOIN dim_developer d ON f.developer_key = d.developer_key
    JOIN dim_repository r ON f.repository_key = r.repository_key
    JOIN dim_event e ON f.event_key = e.event_key
    JOIN dim_technology tech ON f.technology_key = tech.technology_key
    {where_stmt}
    GROUP BY t.hour, e.event_type, tech.category, d.developer_type
    ORDER BY t.hour, event_count DESC
    """
    with eng.connect() as conn:
        return pd.read_sql(text(query), conn)

def olap_pivot(
    engine: Optional[Engine] = None,
    row_dimension: str = "category",
    column_dimension: str = "event_type"
) -> pd.DataFrame:
    eng = engine or get_engine()
    dim_map = {
        "category": "tech.category",
        "event_type": "e.event_type",
        "hour": "t.hour",
        "developer_type": "d.developer_type",
    }
    row_col = dim_map.get(row_dimension.lower(), "tech.category")
    col_col = dim_map.get(column_dimension.lower(), "e.event_type")

    query = f"""
    SELECT
        {row_col} AS row_val,
        {col_col} AS col_val,
        COUNT(f.fact_id) AS val_count
    FROM fact_github_activity f
    JOIN dim_time t ON f.time_key = t.time_key
    JOIN dim_developer d ON f.developer_key = d.developer_key
    JOIN dim_repository r ON f.repository_key = r.repository_key
    JOIN dim_event e ON f.event_key = e.event_key
    JOIN dim_technology tech ON f.technology_key = tech.technology_key
    GROUP BY {row_col}, {col_col}
    """
    with eng.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        return pd.DataFrame()

    pivot_df = df.pivot(index="row_val", columns="col_val", values="val_count").fillna(0).astype(int)
    pivot_df.index.name = row_dimension
    pivot_df.columns.name = column_dimension
    return pivot_df
