"""Empirical benchmark experiments for IEEE/ACM conference paper."""

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parent))
from generate_data import generate_customer_ids, generate_products, generate_stores, generate_transactions
from cleaning.transform_sales import transform_sales_data
from validation.quality_checks import ensure_audit_tables, validate_and_quarantine_sales

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "paper_results"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_PATH = Path(__file__).resolve().parent / "sql" / "audit_and_reporting_schema.sql"


def run_fault_injection_experiment(products_df, stores_df, base_txn_df):
    results = []
    for rate in [0.01, 0.05, 0.10, 0.20]:
        engine = create_engine("sqlite:///:memory:")
        ensure_audit_tables(engine, SCHEMA_PATH)
        df = base_txn_df.copy()
        n = len(df)
        n_corrupt = int(n * rate)
        np.random.seed(42)
        corrupt_idx = np.random.choice(df.index, size=n_corrupt, replace=False)

        for i, idx in enumerate(corrupt_idx):
            fault_type = i % 4
            if fault_type == 0:
                df.loc[idx, "quantity"] = -5
            elif fault_type == 1:
                df.loc[idx, "unit_price"] = df.loc[idx, "unit_price"] * 2.5
            elif fault_type == 2:
                df.loc[idx, "product_id"] = "PROD-9999"
            else:
                df.loc[idx, "timestamp"] = "INVALID-DATE"

        t0 = time.perf_counter()
        valid_df = validate_and_quarantine_sales(df, products_df, stores_df, engine, f"FUNT-{int(rate*100)}")
        elapsed = time.perf_counter() - t0

        rejected = pd.read_sql("SELECT * FROM rejected_sales", engine)
        recall = (len(rejected) / n_corrupt * 100.0) if n_corrupt > 0 else 100.0
        results.append({
            "injected_fault_pct": int(rate * 100),
            "total_rows": n,
            "injected_count": n_corrupt,
            "quarantined_count": len(rejected),
            "recall_pct": round(recall, 2),
            "quality_score_pct": round(len(valid_df) / n * 100.0, 2),
            "validation_latency_s": round(elapsed, 4),
        })
    return pd.DataFrame(results)


def run_scalability_experiment(products_df, stores_df, customers):
    results = []
    for size in [10000, 50000, 100000, 250000]:
        engine = create_engine("sqlite:///:memory:")
        ensure_audit_tables(engine, SCHEMA_PATH)
        txn_df = generate_transactions(products_df, stores_df, customers, num_records=size)

        t0 = time.perf_counter()
        valid_df = validate_and_quarantine_sales(txn_df, products_df, stores_df, engine, f"SCALE-{size}")
        t_val = time.perf_counter() - t0

        t1 = time.perf_counter()
        cleaned_df = transform_sales_data(valid_df)
        t_trans = time.perf_counter() - t1

        t2 = time.perf_counter()
        cleaned_df.to_sql("cleaned_sales", con=engine, if_exists="replace", index=False, chunksize=10000)
        t_load = time.perf_counter() - t2

        total_time = t_val + t_trans + t_load
        results.append({
            "record_count": size,
            "validation_s": round(t_val, 4),
            "transformation_s": round(t_trans, 4),
            "db_load_s": round(t_load, 4),
            "total_etl_s": round(total_time, 4),
            "throughput_rows_per_sec": round(size / total_time, 0),
        })
    return pd.DataFrame(results)


def main():
    products_df = generate_products(1000)
    stores_df = generate_stores(100)
    customers = generate_customer_ids(12000)
    base_txn = generate_transactions(products_df, stores_df, customers, 50000)

    fault_df = run_fault_injection_experiment(products_df, stores_df, base_txn)
    scale_df = run_scalability_experiment(products_df, stores_df, customers)

    fault_df.to_csv(OUT_DIR / "fault_injection_results.csv", index=False)
    scale_df.to_csv(OUT_DIR / "scalability_results.csv", index=False)
    print("\n--- Fault Injection Results ---")
    print(fault_df.to_string(index=False))
    print("\n--- Scalability Benchmark Results ---")
    print(scale_df.to_string(index=False))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(scale_df["record_count"] / 1000, scale_df["total_etl_s"], marker="o", linewidth=2)
    ax1.set_title("ETL Latency vs. Batch Size")
    ax1.set_xlabel("Transaction Records (Thousands)")
    ax1.set_ylabel("Execution Time (seconds)")
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2.bar(scale_df["record_count"].astype(str), scale_df["throughput_rows_per_sec"], color="#2b5c84")
    ax2.set_title("Pipeline Throughput (Rows/sec)")
    ax2.set_xlabel("Batch Size (Records)")
    ax2.set_ylabel("Throughput (rows/sec)")
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "scalability_figure.png", dpi=300)
    print(f"\nSaved publication figure and CSV tables to {OUT_DIR}")

if __name__ == "__main__":
    main()
