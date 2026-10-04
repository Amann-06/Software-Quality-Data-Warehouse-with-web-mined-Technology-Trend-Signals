from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine

from src.utils.config import (
    WAREHOUSE_DB_PATH,
    PROCESSED_DATA_DIR,
    get_raw_data_path,
)
from src.etl.extract import extract_data
from src.etl.transform import transform_data
from src.warehouse.schema import initialize_database, get_table_counts

def load_tables_to_warehouse(
    tables: Dict[str, pd.DataFrame],
    db_path: Optional[Path | str] = None,
    chunksize: int = 5000
) -> Dict[str, int]:
    target_path = Path(db_path) if db_path else WAREHOUSE_DB_PATH
    initialize_database(target_path)

    engine = create_engine(f"sqlite:///{target_path.as_posix()}")

    order = [
        "dim_time",
        "dim_developer",
        "dim_repository",
        "dim_event",
        "dim_technology",
        "fact_github_activity",
    ]

    for table_name in order:
        df = tables[table_name]
        df.to_sql(
            table_name,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=chunksize,
        )

    return get_table_counts(engine)

def save_processed_dataset(df_enriched: pd.DataFrame) -> Path:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = PROCESSED_DATA_DIR / "processed_events.parquet"
    df_enriched.to_parquet(parquet_path, index=False)
    return parquet_path

def run_etl_pipeline(
    csv_path: Optional[Path | str] = None,
    db_path: Optional[Path | str] = None,
    nrows: Optional[int] = None,
) -> Dict[str, Any]:
    raw_path = Path(csv_path) if csv_path else get_raw_data_path()
    target_db = Path(db_path) if db_path else WAREHOUSE_DB_PATH

    raw_df, extract_stats = extract_data(raw_path, nrows=nrows)
    enriched_df, tables = transform_data(raw_df)

    counts = load_tables_to_warehouse(tables, db_path=target_db)
    processed_file = save_processed_dataset(enriched_df)

    return {
        "status": "success",
        "raw_rows": len(raw_df),
        "db_path": str(target_db),
        "processed_file": str(processed_file),
        "table_counts": counts,
        "extract_stats": extract_stats,
    }

if __name__ == "__main__":
    results = run_etl_pipeline()
    print("ETL execution completed successfully.")
    print(f"Table counts: {results['table_counts']}")
    print(f"Database: {results['db_path']}")
