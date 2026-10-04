from pathlib import Path
from typing import Dict, Any, Optional
import sqlite3
from sqlalchemy import create_engine, Engine, text

from src.utils.config import WAREHOUSE_DB_PATH, WAREHOUSE_DB_URI, SQL_DIR

def get_engine(db_uri: Optional[str] = None) -> Engine:
    uri = db_uri or WAREHOUSE_DB_URI
    return create_engine(uri)

def initialize_database(db_path: Optional[Path | str] = None, ddl_path: Optional[Path | str] = None) -> None:
    target_path = Path(db_path) if db_path else WAREHOUSE_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    script_path = Path(ddl_path) if ddl_path else SQL_DIR / "warehouse" / "star_schema.sql"
    if not script_path.exists():
        raise FileNotFoundError(f"Star schema DDL script not found: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        ddl_sql = f.read()

    conn = sqlite3.connect(target_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(ddl_sql)
        conn.commit()
    finally:
        conn.close()

def get_table_counts(engine: Optional[Engine] = None) -> Dict[str, int]:
    eng = engine or get_engine()
    tables = [
        "dim_time",
        "dim_developer",
        "dim_repository",
        "dim_event",
        "dim_technology",
        "fact_github_activity",
    ]
    counts = {}
    with eng.connect() as conn:
        for t in tables:
            try:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                counts[t] = res.scalar() or 0
            except Exception:
                counts[t] = -1
    return counts
