"""Unit and integration tests for validation, quarantine, and transformation."""

import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from cleaning.transform_sales import transform_sales_data
from validation.quality_checks import ensure_audit_tables, validate_and_quarantine_sales


def test_transform_sales_financial_and_date_math():
    raw = pd.DataFrame([
        {
            "transaction_id": "TXN-1",
            "timestamp": "2026-11-14 14:30:00",
            "store_id": "STORE-001",
            "customer_id": "CUST-000001",
            "product_id": "PROD-0001",
            "quantity": 2,
            "unit_price": 50.00,
            "discount_rate": 0.10,
            "total_amount": 90.00,
        }
    ])
    cleaned = transform_sales_data(raw)
    assert cleaned.loc[0, "gross_amount"] == 100.00
    assert cleaned.loc[0, "discount_amount"] == 10.00
    assert cleaned.loc[0, "net_amount"] == 90.00
    assert cleaned.loc[0, "day_of_week"] == "Saturday"
    assert bool(cleaned.loc[0, "is_weekend"]) is True


def test_quarantine_catches_duplicates_negatives_and_anomalies():
    engine = create_engine("sqlite:///:memory:")
    schema_path = Path(__file__).resolve().parent.parent / "src" / "sql" / "audit_and_reporting_schema.sql"
    ensure_audit_tables(engine, schema_path)
    products = pd.DataFrame([{"product_id": "PROD-0001", "unit_price": 100.00}])
    stores = pd.DataFrame([{"store_id": "STORE-001"}])
    raw = pd.DataFrame([
        {"transaction_id": "TXN-OK", "timestamp": "2026-11-15 10:00:00", "store_id": "STORE-001", "customer_id": "C1", "product_id": "PROD-0001", "quantity": 1, "unit_price": 100.00, "discount_rate": 0.0, "total_amount": 100.00},
        {"transaction_id": "TXN-OK", "timestamp": "2026-11-15 10:00:00", "store_id": "STORE-001", "customer_id": "C1", "product_id": "PROD-0001", "quantity": 1, "unit_price": 100.00, "discount_rate": 0.0, "total_amount": 100.00},
        {"transaction_id": "TXN-NEG", "timestamp": "2026-11-15 10:05:00", "store_id": "STORE-001", "customer_id": "C2", "product_id": "PROD-0001", "quantity": -3, "unit_price": 100.00, "discount_rate": 0.0, "total_amount": -300.00},
        {"transaction_id": "TXN-ANOM", "timestamp": "2026-11-15 10:10:00", "store_id": "STORE-001", "customer_id": "C3", "product_id": "PROD-0001", "quantity": 1, "unit_price": 250.00, "discount_rate": 0.0, "total_amount": 250.00},
    ])
    valid = validate_and_quarantine_sales(raw, products, stores, engine, "TEST-RUN-1")
    assert len(valid) == 1
    rejected = pd.read_sql("SELECT * FROM rejected_sales", engine)
    assert len(rejected) == 3
    audit = pd.read_sql("SELECT * FROM data_quality_logs", engine)
    assert audit.loc[0, "quality_score"] == 25.00
