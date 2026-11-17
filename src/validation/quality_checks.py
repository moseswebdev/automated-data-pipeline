"""Data quality validation, anomaly detection, and quarantine engine."""

import logging
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


def ensure_audit_tables(engine, schema_path):
    """Create rejected_sales, data_quality_logs, and reporting_summary tables if missing."""
    sql_script = schema_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in sql_script.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))


def validate_and_quarantine_sales(raw_df, products_df, stores_df, engine, run_id):
    """Validate raw_sales, quarantine rejected rows, and record a data quality audit log."""
    run_ts = datetime.now(timezone.utc).replace(tzinfo=None)
    total_records = len(raw_df)
    logger.info(f"[Run {run_id}] Validating {total_records:,} raw_sales records...")

    df = raw_df.copy()
    reasons = pd.Series("", index=df.index)

    req_cols = ["transaction_id", "timestamp", "store_id", "customer_id", "product_id", "quantity", "unit_price"]
    missing_mask = df[req_cols].isnull().any(axis=1)
    reasons.loc[missing_mask] += "MISSING_REQUIRED_FIELD; "

    dup_mask = df["transaction_id"].duplicated(keep="first") & df["transaction_id"].notnull()
    reasons.loc[dup_mask] += "DUPLICATE_TRANSACTION_ID; "

    parsed_ts = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_date_mask = parsed_ts.isnull() & df["timestamp"].notnull()
    reasons.loc[bad_date_mask] += "INVALID_TIMESTAMP; "

    bad_num_mask = (df["quantity"] <= 0) | (df["unit_price"] <= 0) | (~df["discount_rate"].between(0.0, 1.0))
    reasons.loc[bad_num_mask.fillna(False)] += "INVALID_QUANTITY_PRICE_OR_DISCOUNT; "

    valid_products = set(products_df["product_id"])
    valid_stores = set(stores_df["store_id"])
    fk_mask = (~df["product_id"].isin(valid_products)) | (~df["store_id"].isin(valid_stores))
    reasons.loc[fk_mask] += "UNKNOWN_PRODUCT_OR_STORE_ID; "

    catalog_prices = products_df.set_index("product_id")["price" if "price" in products_df.columns else "unit_price"]
    expected_price = df["product_id"].map(catalog_prices)
    price_drift = ((df["unit_price"] - expected_price).abs() / expected_price) > 0.20
    extreme_qty = df["quantity"] > 50
    anomaly_mask = (price_drift.fillna(False) | extreme_qty)
    reasons.loc[anomaly_mask] += "PRICE_OR_QUANTITY_ANOMALY; "

    rejected_mask = reasons != ""
    valid_df = df.loc[~rejected_mask].copy()
    rejected_df = df.loc[rejected_mask].copy()

    if not rejected_df.empty:
        rejected_df["run_id"] = run_id
        rejected_df["rejection_reason"] = reasons.loc[rejected_mask].str.rstrip("; ")
        rejected_df["rejected_at"] = run_ts
        quarantine_cols = [
            "run_id", "transaction_id", "timestamp", "store_id", "customer_id",
            "product_id", "quantity", "unit_price", "discount_rate", "total_amount",
            "rejection_reason", "rejected_at",
        ]
        rejected_df[quarantine_cols].to_sql("rejected_sales", con=engine, if_exists="append", index=False)
        logger.warning(f"[Run {run_id}] Quarantined {len(rejected_df):,} rejected records into rejected_sales.")
    else:
        logger.info(f"[Run {run_id}] 0 records quarantined.")

    valid_count = len(valid_df)
    rejected_count = len(rejected_df)
    quality_score = round((valid_count / total_records * 100.0) if total_records > 0 else 100.0, 2)
    status = "SUCCESS" if quality_score >= 95.0 else "WARNING"

    audit_row = pd.DataFrame([{
        "run_id": run_id,
        "run_timestamp": run_ts,
        "table_name": "raw_sales",
        "total_records": total_records,
        "valid_records": valid_count,
        "rejected_records": rejected_count,
        "duplicate_records": int(dup_mask.sum()),
        "missing_value_records": int(missing_mask.sum()),
        "anomaly_records": int(anomaly_mask.sum()),
        "quality_score": quality_score,
        "status": status,
    }])
    audit_row.to_sql("data_quality_logs", con=engine, if_exists="append", index=False)
    logger.info(f"[Run {run_id}] Audit logged | Quality Score: {quality_score}% | Status: {status}")

    return valid_df


def validate_cleaned_sales(cleaned_df):
    """Assert post-transformation invariants before loading into cleaned_sales."""
    if cleaned_df.empty:
        raise ValueError("Validation failed: cleaned_sales DataFrame is empty.")
    if cleaned_df.isnull().any().any():
        null_cols = cleaned_df.columns[cleaned_df.isnull().any()].tolist()
        raise ValueError(f"Validation failed: unexpected nulls found in columns {null_cols}")
    if (cleaned_df["net_amount"] < 0).any():
        raise ValieError("Validation failed: negative net_amount values detected.")
