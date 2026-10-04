import json
import re
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

from src.utils.config import TECHNOLOGY_TAXONOMY, PARENT_CATEGORY

def parse_payload(val: Any) -> Dict[str, Any]:
    if pd.isna(val) or val is None:
        return {}
    if isinstance(val, dict):
        return val
    if not isinstance(val, str):
        return {}
    try:
        parsed = json.loads(val)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}

def build_technology_matcher() -> Dict[str, Tuple[str, re.Pattern]]:
    matcher = {}
    for category, tech_list in TECHNOLOGY_TAXONOMY.items():
        for tech in tech_list:
            escaped = re.escape(tech)
            pattern = re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)
            matcher[tech.lower()] = (category, pattern)
    return matcher

TECH_MATCHER = build_technology_matcher()

def detect_technologies(text: str) -> List[Tuple[str, str]]:
    if not text:
        return []
    matches = []
    seen = set()
    for tech, (category, pattern) in TECH_MATCHER.items():
        if pattern.search(text) and tech not in seen:
            seen.add(tech)
            matches.append((tech, category))
    return matches

def clean_and_normalize(df: pd.DataFrame) -> pd.DataFrame:
    df_clean = df.copy()
    df_clean = df_clean.drop_duplicates(subset=["id"]).reset_index(drop=True)
    df_clean["id"] = df_clean["id"].astype("int64")

    df_clean["created_at_dt"] = pd.to_datetime(df_clean["created_at"], utc=True)
    df_clean["date"] = df_clean["created_at_dt"].dt.date.astype(str)
    df_clean["hour"] = df_clean["created_at_dt"].dt.hour
    df_clean["day"] = df_clean["created_at_dt"].dt.day
    df_clean["day_name"] = df_clean["created_at_dt"].dt.day_name()
    df_clean["week"] = df_clean["created_at_dt"].dt.isocalendar().week.astype(int)
    df_clean["month"] = df_clean["created_at_dt"].dt.month
    df_clean["year"] = df_clean["created_at_dt"].dt.year
    df_clean["is_weekend"] = df_clean["created_at_dt"].dt.dayofweek.isin([5, 6]).astype(int)

    df_clean["developer"] = df_clean["developer"].fillna("unknown").astype(str).str.strip()
    df_clean["repository"] = df_clean["repository"].fillna("unknown/unknown").astype(str).str.strip()
    df_clean["event_type"] = df_clean["event_type"].fillna("UnknownEvent").astype(str).str.strip()

    df_clean["is_bot"] = (
        df_clean["developer"].str.lower().str.endswith("[bot]") |
        df_clean["developer"].str.lower().str.startswith("bot-") |
        df_clean["developer"].str.lower().str.contains("action|bot|jenkins", regex=True)
    ).astype(int)

    repo_parts = df_clean["repository"].str.split("/", n=1, expand=True)
    df_clean["repo_owner"] = repo_parts[0].fillna("unknown")
    df_clean["repo_name"] = repo_parts[1].fillna(repo_parts[0])

    return df_clean

def extract_payload_features(df: pd.DataFrame) -> pd.DataFrame:
    df_out = df.copy()

    actions: List[str] = []
    issue_titles: List[str] = []
    comment_bodies: List[str] = []
    labels_list: List[str] = []
    issue_comments_counts: List[int] = []
    defect_proxies: List[int] = []
    has_issues: List[int] = []
    has_prs: List[int] = []
    all_texts: List[str] = []
    primary_techs: List[str] = []
    categories: List[str] = []
    tech_lists: List[str] = []

    for _, row in df_out.iterrows():
        p = parse_payload(row["payload_json"])
        event_type = row["event_type"]

        action = str(p.get("action", "")).strip()
        if not action:
            if event_type == "PushEvent":
                action = "pushed"
            elif event_type == "ForkEvent":
                action = "forked"
            elif event_type == "ReleaseEvent":
                action = "published"
            else:
                action = "occurred"
        actions.append(action)

        issue_obj = p.get("issue") if isinstance(p.get("issue"), dict) else {}
        issue_title = str(issue_obj.get("title", "")).strip() if issue_obj else ""
        issue_comments = int(issue_obj.get("comments", 0)) if issue_obj and isinstance(issue_obj.get("comments"), (int, float)) else 0
        issue_titles.append(issue_title)
        issue_comments_counts.append(issue_comments)

        raw_labels = issue_obj.get("labels", []) if issue_obj else []
        label_names = []
        if isinstance(raw_labels, list):
            for lbl in raw_labels:
                if isinstance(lbl, dict) and "name" in lbl:
                    label_names.append(str(lbl["name"]).lower())
                elif isinstance(lbl, str):
                    label_names.append(lbl.lower())
        labels_str = " ".join(label_names)
        labels_list.append(labels_str)

        comment_obj = p.get("comment") if isinstance(p.get("comment"), dict) else {}
        review_obj = p.get("review") if isinstance(p.get("review"), dict) else {}
        release_obj = p.get("release") if isinstance(p.get("release"), dict) else {}

        comment_body = ""
        if comment_obj:
            comment_body = str(comment_obj.get("body", "")).strip()
        elif review_obj:
            comment_body = str(review_obj.get("body", "")).strip()
        elif release_obj:
            comment_body = str(release_obj.get("body", "") or release_obj.get("name", "")).strip()
        comment_bodies.append(comment_body)

        is_issue = 1 if event_type in ["IssuesEvent", "IssueCommentEvent"] or bool(issue_obj) else 0
        is_pr = 1 if event_type in ["PullRequestEvent", "PullRequestReviewEvent", "PullRequestReviewCommentEvent"] or "pull_request" in p else 0
        has_issues.append(is_issue)
        has_prs.append(is_pr)

        is_defect = 0
        if is_issue:
            defect_keywords = {"bug", "defect", "error", "fail", "broken", "fault", "crash", "fix", "regression", "patch"}
            combined_issue_text = f"{issue_title} {labels_str}".lower()
            if any(k in combined_issue_text for k in defect_keywords):
                is_defect = 1
            else:
                is_defect = 0
        defect_proxies.append(is_defect)

        combined_text = f"{row['repository']} {issue_title} {labels_str} {comment_body[:150]}"
        all_texts.append(combined_text.strip())

        detected = detect_technologies(f"{row['repository']} {issue_title} {labels_str}")
        if detected:
            primary_techs.append(detected[0][0])
            categories.append(detected[0][1])
            tech_lists.append(";".join([t[0] for t in detected]))
        else:
            primary_techs.append("general")
            categories.append("Development")
            tech_lists.append("general")

    df_out["action"] = actions
    df_out["issue_title"] = issue_titles
    df_out["comment_body"] = comment_bodies
    df_out["issue_labels"] = labels_list
    df_out["issue_comments_count"] = issue_comments_counts
    df_out["is_defect_proxy"] = defect_proxies
    df_out["has_issue_flag"] = has_issues
    df_out["has_pr_flag"] = has_prs
    df_out["is_review_event"] = df_out["event_type"].isin(["PullRequestReviewEvent", "PullRequestReviewCommentEvent"]).astype(int)
    df_out["extracted_text"] = all_texts
    df_out["text_length"] = df_out["extracted_text"].str.len()
    df_out["primary_technology"] = primary_techs
    df_out["technology_category"] = categories
    df_out["technologies"] = tech_lists

    return df_out

def build_star_schema_tables(df_enriched: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    # 1. dim_time
    time_df = df_enriched[[
        "created_at", "date", "hour", "day", "day_name", "week", "month", "year", "is_weekend"
    ]].drop_duplicates().reset_index(drop=True)
    time_df["time_key"] = time_df.index + 1
    time_df = time_df[[
        "time_key", "created_at", "date", "hour", "day", "day_name", "week", "month", "year", "is_weekend"
    ]]

    # 2. dim_developer
    dev_df = df_enriched[[
        "developer", "is_bot"
    ]].drop_duplicates(subset=["developer"]).reset_index(drop=True)
    dev_df["developer_key"] = dev_df.index + 1
    dev_df["developer_type"] = np.where(dev_df["is_bot"] == 1, "bot", "user")
    dev_df = dev_df[["developer_key", "developer", "is_bot", "developer_type"]].rename(
        columns={"developer": "developer_login"}
    )

    # 3. dim_repository
    repo_df = df_enriched[[
        "repository", "repo_owner", "repo_name"
    ]].drop_duplicates(subset=["repository"]).reset_index(drop=True)
    repo_df["repository_key"] = repo_df.index + 1
    repo_df = repo_df[["repository_key", "repository", "repo_owner", "repo_name"]].rename(
        columns={"repository": "full_name", "repo_owner": "owner"}
    )

    # 4. dim_event
    event_df = df_enriched[[
        "event_type", "action", "is_defect_proxy", "is_review_event"
    ]].drop_duplicates().reset_index(drop=True)
    event_df["event_key"] = event_df.index + 1
    event_df = event_df[["event_key", "event_type", "action", "is_defect_proxy", "is_review_event"]]

    # 5. dim_technology
    tech_df = df_enriched[[
        "primary_technology", "technology_category"
    ]].drop_duplicates().reset_index(drop=True)
    tech_df["technology_key"] = tech_df.index + 1
    tech_df["parent_category"] = PARENT_CATEGORY
    tech_df = tech_df[[
        "technology_key", "primary_technology", "technology_category", "parent_category"
    ]].rename(
        columns={"primary_technology": "technology_name", "technology_category": "category"}
    )

    # 6. fact_github_activity
    fact_work = df_enriched.copy()
    fact_work = fact_work.merge(time_df[["time_key", "created_at"]], on="created_at", how="left")
    fact_work = fact_work.merge(dev_df[["developer_key", "developer_login"]], left_on="developer", right_on="developer_login", how="left")
    fact_work = fact_work.merge(repo_df[["repository_key", "full_name"]], left_on="repository", right_on="full_name", how="left")
    fact_work = fact_work.merge(
        event_df[["event_key", "event_type", "action", "is_defect_proxy", "is_review_event"]],
        on=["event_type", "action", "is_defect_proxy", "is_review_event"],
        how="left"
    )
    fact_work = fact_work.merge(
        tech_df[["technology_key", "technology_name", "category"]],
        left_on=["primary_technology", "technology_category"],
        right_on=["technology_name", "category"],
        how="left"
    )

    fact_work["fact_id"] = fact_work.index + 1
    fact_work["activity_count"] = 1

    fact_table = fact_work[[
        "fact_id",
        "id",
        "time_key",
        "developer_key",
        "repository_key",
        "event_key",
        "technology_key",
        "activity_count",
        "issue_comments_count",
        "text_length",
        "has_issue_flag",
        "has_pr_flag"
    ]].rename(columns={"id": "event_id"})

    return {
        "dim_time": time_df,
        "dim_developer": dev_df,
        "dim_repository": repo_df,
        "dim_event": event_df,
        "dim_technology": tech_df,
        "fact_github_activity": fact_table
    }

def transform_data(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    df_clean = clean_and_normalize(df_raw)
    df_enriched = extract_payload_features(df_clean)
    tables = build_star_schema_tables(df_enriched)
    return df_enriched, tables
