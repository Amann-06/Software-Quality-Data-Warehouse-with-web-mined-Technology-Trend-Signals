import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"

RAW_DATA_FILE = RAW_DATA_DIR / "50kDATASET.csv"
FALLBACK_DATA_FILE = BASE_DIR / "50kDATASET.csv"
WAREHOUSE_DB_PATH = PROCESSED_DATA_DIR / "warehouse.db"
WAREHOUSE_DB_URI = f"sqlite:///{WAREHOUSE_DB_PATH.as_posix()}"

EXPECTED_COLUMNS = [
    "id",
    "created_at",
    "event_type",
    "developer",
    "repository",
    "payload_json",
]

SUPPORTED_EVENT_TYPES = [
    "PushEvent",
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "PullRequestReviewCommentEvent",
    "IssuesEvent",
    "IssueCommentEvent",
    "ForkEvent",
    "ReleaseEvent",
]

TECHNOLOGY_TAXONOMY = {
    "Web": [
        "react", "vue", "angular", "svelte", "nextjs", "next.js", "html", "css",
        "javascript", "typescript", "flask", "django", "fastapi", "express",
        "tailwind", "nodejs", "node", "webpack", "vite", "frontend"
    ],
    "DevOps": [
        "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
        "github-actions", "actions", "helm", "ci-cd", "argocd", "prometheus", "grafana"
    ],
    "Infrastructure": [
        "aws", "azure", "gcp", "linux", "cloud", "serverless", "nginx",
        "openstack", "lambda", "ec2", "s3", "azurerm"
    ],
    "Databases": [
        "postgres", "postgresql", "mysql", "mongodb", "redis", "sqlite",
        "opensearch", "elasticsearch", "cassandra", "dynamodb", "clickhouse"
    ],
    "Data": [
        "python", "pandas", "numpy", "spark", "hadoop", "kafka", "pytorch",
        "tensorflow", "machine-learning", "deep-learning", "scikit", "nlp", "llm"
    ],
    "Mobile": [
        "android", "ios", "swift", "kotlin", "flutter", "react-native"
    ],
    "Development": [
        "rust", "golang", "go", "cpp", "c++", "java", "csharp", "dotnet",
        ".net", "php", "ruby", "graphql", "rest", "api", "git", "cli"
    ],
}

PARENT_CATEGORY = "Software"

def get_raw_data_path() -> Path:
    if RAW_DATA_FILE.exists():
        return RAW_DATA_FILE
    if FALLBACK_DATA_FILE.exists():
        return FALLBACK_DATA_FILE
    raise FileNotFoundError(
        f"Dataset not found at {RAW_DATA_FILE} or {FALLBACK_DATA_FILE}."
    )
