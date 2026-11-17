"""Automated business report generator exporting CSV and Excel reports."""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DATABASE_URL, REPORTS_DIR

logger = logging.getLogger("reporting")


def build_reports_and_summary(engine):
    """Query cleaned data, update reporting_summary, and export 5 reports."""
    gen_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    daily_sql = """
    SELECT
        sale_date,
        COUNT(transaction_id) AS total_transactions,
        SUM(quantity) AS total_units_sold,
        ROUND(SUM(gross_amount), 2) AS gross_revenue,
        ROUND(SUM(discount_amount), 2) AS total_discounts,
        ROUND(SUM(net_amount), 2) AS net_revenue,
        ROUND(AVG(net_amount), 2) AS avg_order_value
    FROM cleaned_sales
    GROUP BY sale_date
    ORDER BY sale_date DESC
    """
    daily_df = pd.read_sql(daily_sql, engine)

    weekly_sql = """
    SELECT
        s.sale_year,
        s.sale_month,
        st.region,
        st.store_tier,
        COUNT(s.transaction_id) AS total_orders,
        SUM(s.quantity) AS units_sold,
        ROUND(SUM(s.discount_amount), 2) AS total_discounts,
        ROUND(SUM(s.net_amount), 2) AS net_revenue
    FROM cleaned_sales s
    JOIN stores st ON s.store_id = st.store_id
    GROUP BY s.sale_year, s.sale_month, st.region, st.store_tier
    ORDER BY s.sale_year DESC, s.sale_month DESC, net_revenue DESC
    """
    weekly_df = pd.read_sql(weekly_sql, engine)

    monthly_sql = """
    SELECT
        s.sale_year,
        s.sale_month,
        p.category,
        COUNT(s.transaction_id) AS total_transactions,
        SUM(s.quantity) AS total_units,
        ROUND(SUM(s.gross_amount), 2) AS gross_revenue,
        ROUND(SUM(s.discount_amount), 2) AS total_discounts,
        ROUND(SUM(s.net_amount), 2) AS net_revenue
    FROM cleaned_sales s, products p
    WHERE s.product_id = p.product_id
    GROUP BY s.sale_year, s.sale_month, p.category
    ORDER BY s.sale_year DESC, s.sale_month DESC, net_revenue DESC
    """
    monthly_df = pd.read_sql(monthly_sql, engine)

    dq_df = pd.read_sql("SELECT * FROM data_quality_logs ORDER BY run_timestamp DESC", engine)

    inv_sql = """
    SELECT
        i.store_id,
        st.store_name,
        st.region,
        i.product_id,
        p.product_name,
        p.category,
        i.units_sold_12m,
        i.reorder_point,
        i.stock_on_hand,
        (i.reorder_point - i.stock_on_hand) AS shortfall_units,
        i.last_updated
    FROM inventory i, products p, stores st
    WHERE i.product_id = p.product_id AND i.store_id = st.store_id AND i.needs_reorder = 1
    ORDER BY shortfall_units DESC, i.units_sold_12m DESC
    """
    inv_exceptions_df = pd.read_sql(inv_sql, engine)

    low_stock_count = len(inv_exceptions_df)
    summary_df = daily_df[["sale_date", "total_transactions", "total_units_sold", "gross_revenue", "total_discounts", "net_revenue"]].copy()
    summary_df = summary_df.rename(columns={"sale_date": "report_date"})
    summary_df["period_type"] = "DAILY"
    summary_df["low_stock_sku_count"] = low_stock_count
    summary_df["generated_at"] = gen_ts

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM reporting_summary;"))
    summary_df.to_sql("reporting_summary", con=engine, if_exists="append", index=False)

    reports = {
        "daily_sales_report": daily_df,
        "weekly_operations_report": weekly_df,
        "monthly_management_report": monthly_df,
        "data_quality_report": dq_df,
        "inventory_exception_report": inv_exceptions_df,
    }

    for name, df in reports.items():
        csv_path = REPORTS_DIR / f"{name}.csv"
        xlsx_path = REPORTS_DIR / f"{name}.xlsx"
        df.to_csv(csv_path, index=False)
        df.to_excel(xlsx_path, index=False, sheet_name="Report")
        print(f"Exported {name} ({len(df):,} rows) -> CSV & Excel")


def main():
    engine = create_engine(DATABASE_URL)
    build_reports_and_summary(engine)

if __name__ == "__main__":
    main()
