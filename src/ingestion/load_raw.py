"""Load synthetic CSV datasets into the database raw staging tables."""

import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR, DATABASE_URL


def init_schema(engine):
    """Create staging tables if they do not already exist."""
    schema_sql = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in schema_sql.strip().split(";"):
            if statement.strip():
                conn.execute(text(statement))


def load_csv_to_table(engine, csv_name, table_name, date_cols=None):
    """Read a CSV from data/ and load records into the target database table."""
    file_path = DATA_DIR / csv_name
    df = pd.read_csv(file_path, parse_dates=date_cols or [])
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    return len(df)


def main():
    """Initialize schema, clear existing staging rows, and load all CSV datasets."""
    engine = create_engine(DATABASE_URL)
    init_schema(engine)

    with engine.begin() as conn:
        for table in ["inventory", "raw_sales", "products", "stores"]:
            conn.execute(text(f"DELETE FROM {table};"))

    load_plan = [
        ("products.csv", "products", None),
        ("stores.csv", "stores", None),
        ("transactions.csv", "raw_sales", ["timestamp"]),
        ("inventory.csv", "inventory", ["last_updated"]),
    ]

    for csv_file, table, date_cols in load_plan:
        rows = load_csv_to_table(engine, csv_file, table, date_cols)
        print(f"Loaded {rows:,} rows from {csv_file} -> {table}")


if __name__ == "__main__":
    main()
