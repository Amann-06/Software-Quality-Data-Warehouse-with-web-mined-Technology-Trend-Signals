from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

def prepare_datetime_index(df: pd.DataFrame, time_col: str = "created_at_dt") -> pd.DataFrame:
    df_ts = df.copy()
    if time_col not in df_ts.columns:
        if "created_at" in df_ts.columns:
            df_ts[time_col] = pd.to_datetime(df_ts["created_at"], utc=True)
        else:
            return pd.DataFrame()
    elif not pd.api.types.is_datetime64_any_dtype(df_ts[time_col]):
        df_ts[time_col] = pd.to_datetime(df_ts[time_col], utc=True)

    return df_ts.sort_values(by=time_col).reset_index(drop=True)

def compute_hourly_activity(
    df: pd.DataFrame,
    time_col: str = "created_at_dt",
    rolling_window: int = 3
) -> pd.DataFrame:
    df_ts = prepare_datetime_index(df, time_col=time_col)
    if df_ts.empty:
        return pd.DataFrame()

    df_ts["time_bucket"] = df_ts[time_col].dt.floor("h")

    agg_spec = {
        "id": "count",
        "developer": "nunique",
        "repository": "nunique",
    }
    if "is_defect_proxy" in df_ts.columns:
        agg_spec["is_defect_proxy"] = "sum"

    hourly = df_ts.groupby("time_bucket").agg(agg_spec).rename(
        columns={
            "id": "event_count",
            "developer": "active_developers",
            "repository": "active_repositories",
            "is_defect_proxy": "defect_proxies",
        }
    ).reset_index()

    hourly["rolling_mean"] = hourly["event_count"].rolling(window=rolling_window, min_periods=1).mean().round(2)
    hourly["rolling_std"] = hourly["event_count"].rolling(window=rolling_window, min_periods=1).std().fillna(0).round(2)
    hourly["activity_velocity"] = hourly["event_count"].diff().fillna(0)

    return hourly

def compute_event_type_series(
    df: pd.DataFrame,
    time_col: str = "created_at_dt"
) -> pd.DataFrame:
    df_ts = prepare_datetime_index(df, time_col=time_col)
    if df_ts.empty or "event_type" not in df_ts.columns:
        return pd.DataFrame()

    df_ts["time_bucket"] = df_ts[time_col].dt.floor("h")
    grouped = df_ts.groupby(["time_bucket", "event_type"]).size().unstack(fill_value=0)
    return grouped.reset_index()

def compute_category_series(
    df: pd.DataFrame,
    time_col: str = "created_at_dt",
    category_col: str = "technology_category"
) -> pd.DataFrame:
    df_ts = prepare_datetime_index(df, time_col=time_col)
    if df_ts.empty or category_col not in df_ts.columns:
        return pd.DataFrame()

    df_ts["time_bucket"] = df_ts[time_col].dt.floor("h")
    grouped = df_ts.groupby(["time_bucket", category_col]).size().unstack(fill_value=0)
    return grouped.reset_index()

def compute_trend_summary(hourly_df: pd.DataFrame) -> Dict[str, Any]:
    if hourly_df.empty or "event_count" not in hourly_df.columns:
        return {
            "total_events": 0,
            "mean_hourly_events": 0,
            "peak_hour": None,
            "peak_count": 0,
            "trough_hour": None,
            "trough_count": 0,
            "std_dev": 0,
            "trend_direction": "stable",
        }

    peak_row = hourly_df.loc[hourly_df["event_count"].idxmax()]
    trough_row = hourly_df.loc[hourly_df["event_count"].idxmin()]
    mean_val = float(hourly_df["event_count"].mean())
    std_val = float(hourly_df["event_count"].std()) if len(hourly_df) > 1 else 0.0

    if len(hourly_df) >= 2:
        first_half = hourly_df["event_count"].iloc[:len(hourly_df)//2].mean()
        second_half = hourly_df["event_count"].iloc[len(hourly_df)//2:].mean()
        if second_half > first_half * 1.05:
            direction = "increasing"
        elif second_half < first_half * 0.95:
            direction = "decreasing"
        else:
            direction = "stable"
    else:
        direction = "stable"

    return {
        "total_events": int(hourly_df["event_count"].sum()),
        "mean_hourly_events": round(mean_val, 2),
        "peak_hour": str(peak_row["time_bucket"]),
        "peak_count": int(peak_row["event_count"]),
        "trough_hour": str(trough_row["time_bucket"]),
        "trough_count": int(trough_row["event_count"]),
        "std_dev": round(std_val, 2),
        "trend_direction": direction,
    }
