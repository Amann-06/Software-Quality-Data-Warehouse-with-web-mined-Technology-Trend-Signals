-- OLAP Analysis Queries for Software Quality Data Warehouse
-- Demonstrates Roll-up, Drill-down, Slice, Dice, and Pivot operations

-- 1. ROLL-UP OPERATION:
-- Aggregate activity counts moving up the time dimension hierarchy (Hour -> Day -> Week -> Month)
SELECT
    t.month,
    t.week,
    t.day,
    t.hour,
    COUNT(f.fact_id) AS total_events,
    SUM(e.is_defect_proxy) AS defect_proxy_count,
    COUNT(DISTINCT f.repository_key) AS active_repos,
    COUNT(DISTINCT f.developer_key) AS active_devs
FROM fact_github_activity f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_event e ON f.event_key = e.event_key
GROUP BY t.month, t.week, t.day, t.hour
ORDER BY t.hour;

-- 2. DRILL-DOWN OPERATION:
-- Break down a specific day's activity down to the hour and event type
SELECT
    t.date,
    t.hour,
    e.event_type,
    e.action,
    COUNT(f.fact_id) AS event_count,
    COUNT(DISTINCT f.developer_key) AS unique_contributors
FROM fact_github_activity f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_event e ON f.event_key = e.event_key
WHERE t.date = '2026-09-01'
GROUP BY t.date, t.hour, e.event_type, e.action
ORDER BY t.hour ASC, event_count DESC;

-- 3. SLICE OPERATION:
-- Fix single dimension: Event Type = 'IssuesEvent' (Defect proxy analysis across repositories)
SELECT
    r.full_name AS repository,
    tech.category AS technology_category,
    COUNT(f.fact_id) AS issue_count,
    SUM(f.issue_comments_count) AS total_comments,
    COUNT(DISTINCT f.developer_key) AS reporters_count
FROM fact_github_activity f
JOIN dim_event e ON f.event_key = e.event_key
JOIN dim_repository r ON f.repository_key = r.repository_key
JOIN dim_technology tech ON f.technology_key = tech.technology_key
WHERE e.event_type = 'IssuesEvent'
GROUP BY r.full_name, tech.category
ORDER BY issue_count DESC
LIMIT 25;

-- 4. DICE OPERATION:
-- Multi-dimensional filter: Event types IN ('PullRequestEvent', 'IssuesEvent')
-- AND Technology category IN ('DevOps', 'Web')
-- AND Hour BETWEEN 8 AND 14
SELECT
    t.hour,
    e.event_type,
    tech.category,
    tech.technology_name,
    COUNT(f.fact_id) AS event_count
FROM fact_github_activity f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_event e ON f.event_key = e.event_key
JOIN dim_technology tech ON f.technology_key = tech.technology_key
WHERE e.event_type IN ('PullRequestEvent', 'IssuesEvent')
  AND tech.category IN ('DevOps', 'Web')
  AND t.hour BETWEEN 8 AND 14
GROUP BY t.hour, e.event_type, tech.category, tech.technology_name
ORDER BY t.hour ASC, event_count DESC;

-- 5. PIVOT OPERATION:
-- Cross-tabulate Technology Category across Event Types using conditional aggregation
SELECT
    tech.category,
    SUM(CASE WHEN e.event_type = 'PushEvent' THEN 1 ELSE 0 END) AS push_events,
    SUM(CASE WHEN e.event_type = 'PullRequestEvent' THEN 1 ELSE 0 END) AS pr_events,
    SUM(CASE WHEN e.event_type = 'IssuesEvent' THEN 1 ELSE 0 END) AS issue_events,
    SUM(CASE WHEN e.event_type = 'IssueCommentEvent' THEN 1 ELSE 0 END) AS comment_events,
    SUM(CASE WHEN e.event_type = 'ReleaseEvent' THEN 1 ELSE 0 END) AS release_events,
    COUNT(f.fact_id) AS total_activity
FROM fact_github_activity f
JOIN dim_event e ON f.event_key = e.event_key
JOIN dim_technology tech ON f.technology_key = tech.technology_key
GROUP BY tech.category
ORDER BY total_activity DESC;
