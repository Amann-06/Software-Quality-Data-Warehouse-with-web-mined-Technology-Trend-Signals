-- Google BigQuery extraction query for GitHub Archive
-- Source table: `githubarchive.day.20260901`

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
