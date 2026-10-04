from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from src.utils.config import get_raw_data_path, EXPECTED_COLUMNS

def validate_columns(df: pd.DataFrame) -> None:
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

def summarize_extraction(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "missing_values": df.isnull().sum().to_dict(),
        "event_distribution": df["event_type"].value_counts().to_dict(),
    }

def extract_data(
    file_path: Optional[Path | str] = None,
    nrows: Optional[int] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    path = Path(file_path) if file_path else get_raw_data_path()
    if not path.exists():
        raise FileNotFoundError(f"Source CSV file does not exist: {path}")

    df = pd.read_csv(path, nrows=nrows)
    validate_columns(df)
    summary = summarize_extraction(df)
    return df, summary

if __name__ == "__main__":
    data, stats = extract_data()
    print(f"Extracted {stats['row_count']} rows with columns: {stats['columns']}")
    print(f"Event distribution: {stats['event_distribution']}")
