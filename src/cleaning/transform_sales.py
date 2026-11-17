"""Transform raw_sales into enriched cleaned_sales with quarantine and DQ audit logging."""

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DATABASE_URL, LOGS_DIR
from validation.quality_checks import ensure_audit_tables, validate_and_quarantine_sales, validate_cleaned_sales


def configure_logging():
    log_file = LOGS_DIR / "pipeline.log"
    logging.basicConfig(level=logging.INFO, format="{asctime} - {levelname} - {name} - {message}", style="{", handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)])
    return logging.getLogger("transform_sales")


def transform_sales_data(raw_df):
    df = raw_df.copy()
    ts = pd.to_datetime(df["timestamp"])
    df["transaction_timestamp"] = ts
    df["sale_date"] = ts.dt.date
    df["sale_year"] = ts.dt.year
    df["sale_month"] = ts.dt.month
    df["day_of_week"] = ts.dt.day_name()
    df["is_weekend"] = ts.dt.day_of_week >= 4
    df["gross_amount"] = (df["quantity"] * df["unit_price"]).round(2)
    df["discount_amount"] = (df["gross_amount"] * df["discount_rate"]).round(2)
    df["net_amount"] = (df["gross_amount"] - df["discount_amount"]).round(2)
    df["processed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    cols = ["transaction_id", "transaction_timestamp", "sale_date", "sale_year", "sale_month", "day_of_week", "is_weekend", "store_id", "customer_id", "product_id", "quantity", "unit_price", "gross_amount", "discount_rate", "discount_amount", "net_amount", "processed_at"]
    return df[cols]


def main():
    logger = configure_logging()
    engine = create_engine(DATABASE_URL)
    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    clean_schema = (Path(__file__).resolve().parent / "cleaned_schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(clean_schema))

    audit_schema_path = Path(__file__).resolve().parent.parent / "sql" / "audit_and_reporting_schema.sql"
    ensure_audit_tables(engine, audit_schema_path)

    raw_df = pd.read_sql("SELECT * FROM raw_sales", engine)
    products_df = pd.read_sql("SELECT product_id, unit_price FROM products", engine)
    stores_df = pd.read_sql("SELECT store_id FROM stores", engine)

    validated_df = validate_and_quarantine_sales(raw_df, products_df, stores_df, engine, run_id)
    cleaned_df = transform_sales_data(validated_df)
    validate_cleaned_sales(cleaned_df)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM cleaned_sales;"))

    cleaned_df.to_sql("cleaned_sales", con=engine, if_exists="append", index=False, chunksize=5000)
    logger.info(f"[Run {run_id}] Loaded {len(cleaned_df):,} clean records into cleaned_sales.")


if __name__ == "__main__":
    main()
