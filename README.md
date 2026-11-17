# Automated Business Reporting, Data Cleaning & Quality Monitoring System

End-to-end Python and SQL data engineering platform that ingests retail sales and inventory data, enforces row-level data quality and anomaly quarantine rules, loads curated analytics tables, exports automated CSV/Excel executive reports, and monitors pipeline health in Streamlit.

## Architecture

```text
+-------------------+      +------------------------+      +-----------------------+
|  Synthetic / Raw  | ---> |  Ingestion & Schema    | ---> |  Validation &         |
|  Retail CSVs      |      |  Loader (SQLAlchemy)   |      |  Quarantine Engine    |
+-------------------+      +------------------------+      +-----------------------+
                                                                 |            |
                                              Valid Rows         |            | Rejected / Anomalies
                                              v                  |            v
+-------------------+      +------------------------+      +-----------------------+
|  Streamlit Live   | <--- |  Curated Analytics &   |      |  rejected_sales &     |
|  Dashboard & XLSX |      |  cleaned_sales Tables  |      |  data_quality_logs    |
+-------------------+      +------------------------+      +-----------------------+
```

## Quickstart

1. **Activate virtual environment:** `venv\Scripts\activate`
2. **Generate 50,000+ synthetic retail records:** `python src\generate_data.py`
3. **Run full ETL & automated reporting:** `python src\run_pipeline.py`
4. **Launch Streamlit monitoring dashboard:** `streamlit run dashboard\app.py`
5. **Run automated test suite:** `pytest -v`

## Optional PostgreSQL via Docker

```bash
docker-compose up -d
set DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/data_pipeline
python src\run_pipeline.py
```