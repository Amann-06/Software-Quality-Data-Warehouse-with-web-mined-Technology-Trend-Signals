# Data Directory Setup

This directory organizes raw and processed data assets for the Software Quality Data Warehouse.

## Directory Structure

- `data/raw/`: Contains original data exports. Place `50kDATASET.csv` here.
- `data/processed/`: Contains intermediate analytical extracts, cleaned features, and SQLite analytical warehouse file (`warehouse.db`).

## Setup Instructions

1. Obtain `50kDATASET.csv` (GitHub Archive 50K event export from BigQuery).
2. Place the file at `data/raw/50kDATASET.csv`.
3. Run the ETL pipeline:
   ```bash
   python -m src.etl.load
   ```
