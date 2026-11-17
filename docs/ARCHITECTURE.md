# Technical Architecture: Automated Business Reporting, Data Cleaning and Quality Monitoring System

## 1. System Overview

The **Automated Business Reporting, Data Cleaning and Quality Monitoring System** is a modular Python and SQL data engineering platform designed to eliminate manual spreadsheet reporting. It automates raw data ingestion, row-level data quality validation, anomaly quarantine, dimensional enrichment, relational storage, multi-format report generation (CSV/Excel), and live operational monitoring.

### Design Principles
- **Zero Silent Data Loss:** Invalid or anomalous records are never dropped silently; every failing row is tagged with a diagnostic reason and quarantined in `rejected_sales`.
- **Database Portability:** Built on SQLAlchemy Core/ORM abstractions, allowing seamless switching between local SQLite (`data/data_pipeline.db`) and containerized PostgreSQL (`docker-compose.yml`) via a single `DATABASE_URL` environment variable.
- **Idempotent Execution:** Every pipeline stage supports safe re-runs without duplicating master records or corrupting aggregate summaries.
- **Full Observability:** Dual console/file logging (`logs/pipeline.log`), run-level quality scoring (`data_quality_logs`), and automated CI verification (`.github/workflows/ci.yml`).

---

## 2. End-to-End Data Flow

```text
  [1. Data Generation / Sources]
  products.csv (1k) | stores.csv (100) | transactions.csv (50k) | inventory.csv (47.9k)
                 |
                 v
  [2. Raw Ingestion Layer]  --->  src/ingestion/load_raw.py
  Loads staging tables (products, stores, raw_sales, inventory) in FK-safe order
                 |
                 v
  [3. Validation and Quarantine Engine]  --->  src/validation/quality_checks.py
  Evaluates 6 rule categories: Nulls, Duplicates, Dates, Numerics, FKs, Price/Qty Anomalies
         /               \
  (Pass)                  (Fail)
    |                       |
    v                       v
  [4. Transformation]     [Quarantine and Audit Tables]
  src/cleaning/           rejected_sales (row-level diagnostics)
  transform_sales.py      data_quality_logs (run quality score)
    |
    v
  [5. Curated Analytics Layer]  --->  cleaned_sales and reporting_summary
         /               \
        v                 v
  [6a. Automated Reports] [6b. Live Monitoring Dashboard]
  src/reporting/          dashboard/app.py (Streamlit)
  5 CSV + 5 XLSX files    Interactive filters, KPIs, and audit tabs
```

---

## 3. Relational Database Schema

### Staging and Master Dimension Tables
- **`products`:** Master catalog (`product_id` PK, `product_name`, `category`, `unit_price`).
- **`stores`:** Retail locations (`store_id` PK, `store_name`, `city`, `state`, `region`, `store_tier`).
- **`raw_sales`:** Unfiltered transaction landing table (`transaction_id` PK, `timestamp`, `store_id` FK, `customer_id`, `product_id` FK, `quantity`, `unit_price`, `discount_rate`, `total_amount`).
- **`inventory`:** Store-by-product stock tracking (`(store_id, product_id)` composite PK, `units_sold_12m`, `reorder_point`, `stock_on_hand`, `needs_reorder`, `last_updated`).

### Curated Analytics and Audit Tables
- **`cleaned_sales`:** Enriched fact table storing validated transactions alongside derived calendar attributes (`sale_date`, `sale_year`, `sale_month`, `day_of_week`, `is_weekend`) and financial breakdowns (`gross_amount`, `discount_amount`, `net_amount`, `processed_at`).
- **`rejected_sales`:** Quarantine store capturing failed records (`rejection_id` PK, `run_id`, original payload columns, `rejection_reason`, `rejected_at`).
- **`data_quality_logs`:** Execution audit history (`run_id` PK, `run_timestamp`, `table_name`, `total_records`, `valid_records`, `rejected_records`, `duplicate_records`, `missing_value_records`, `anomaly_records`, `quality_score`, `status`).
- **`reporting_summary`:** Pre-aggregated daily/periodic KPIs (`(report_date, period_type)` composite PK, `total_transactions`, `total_units_sold`, `gross_revenue`, `total_discounts`, `net_revenue`, `low_stock_sku_count`, `generated_at`).

---

## 4. Data Quality Rules and Quarantine Logic

Every batch processed by `validate_and_quarantine_sales()` is evaluated against six deterministic checks:

| Rule Category | Validation Condition | Quarantine Tag |
| :--- | :--- | :--- |
| **Completeness** | Required keys (`transaction_id`, `timestamp`, `store_id`, `customer_id`, `product_id`, `quantity`, `unit_price`) must not be null | `MISSING_REQUIRED_FIELD` |
| **Uniqueness** | `transaction_id` must be unique within the ingestion batch | `DUPLICATE_TRANSACTION_ID` |
| **Temporal Validity** | `timestamp` must parse into a valid ISO datetime | `INVALID_TIMESTAMP` |
| **Domain Bounds** | `quantity > 0`, `unit_price > 0`, and `0.0 <= discount_rate <= 1.0` | `INVALID_QUANTITY_PRICE_OR_DISCOUNT` |
| **Referential Integrity** | `product_id` and `store_id` must exist in master dimension tables | `UNKNOWN_PRODUCT_OR_STORE_ID` |
| **Anomaly Detection** | Transaction `unit_price` within 20% of catalog `unit_price` and `quantity <= 50` | `PRICE_OR_QUANTITY_ANOMALY` |

The run-level **Data Quality Score** is computed as `(valid_records / total_records) * 100`. Runs scoring `>= 95.0%` are marked `SUCCESS`; runs below `95.0%` are flagged `WARNING` for operational review.

---

## 5. Orchestration, Testing and Deployment

- **Pipeline Orchestrator (`src/run_pipeline.py`):** Chains `load_raw` -> `transform_sales` -> `generate_reports` into a single deterministic entrypoint.
- **Local Scheduling:** Configured via Windows Task Scheduler (`AutomatedDataPipeline`) to execute daily at `06:00`.
- **Containerized Database (`docker-compose.yml`):** Provisions PostgreSQL 16 with automatic DDL initialization (`01_schema.sql` and `02_cleaned_schema.sql`) for production parity.
- **Continuous Integration (`.github/workflows/ci.yml`):** GitHub Actions automatically runs `pytest -v` on every push to `main` to verify financial calculations, date derivations, quarantine routing, and audit logging.