"""Streamlit Monitoring and Business Analytics Dashboard."""

import sys
from pathlib import Path
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from config import DATABASE_URL

st.set_page_config(page_title="Data Quality and Reporting Dashboard", layout="wide")


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL)


@st.cache_data(ttl=60)
def load_data():
    engine = get_engine()
    sales = pd.read_sql("SELECT cs.*, p.product_name, p.category, s.store_name, s.region, s.store_tier FROM cleaned_sales cs JOIN products p ON cs.product_id = p.product_id JOIN stores s ON cs.store_id = s.store_id", engine)
    sales["sale_date"] = pd.to_datetime(sales["sale_date"]).dt.date
    dq_logs = pd.read_sql("SELECT * FROM data_quality_logs ORDER BY run_timestamp DESC", engine)
    rejected = pd.read_sql("SELECT * FROM rejected_sales ORDER BY rejected_at DESC", engine)
    inventory = pd.read_sql("SELECT * FROM inventory", engine)
    return sales, dq_logs, rejected, inventory


sales_df, dq_df, rejected_df, inv_df = load_data()

st.title("Automated Business Reporting and Data Quality Monitor")
st.caption("Real-time pipeline observability, quarantine audits, and retail performance analytics")

st.sidebar.header("Interactive Filters")
min_date, max_date = sales_df["sale_date"].min(), sales_df["sale_date"].max()
date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

regions = ["All"] + sorted(sales_df["region"].unique().tolist())
sel_region = st.sidebar.selectbox("Region", regions)

categories = ["All"] + sorted(sales_df["category"].unique().tolist())
sel_category = st.sidebar.selectbox("Product Category", categories)

filtered = sales_df.copy()
if len(date_range) == 2:
    filtered = filtered[filtered["sale_date"].between(date_range[0], date_range[1])]
if sel_region != "All":
    filtered = filtered[filtered["region"] == sel_region]
if sel_category != "All":
    filtered = filtered[filtered["category"] == sel_category]

st.subheader("Pipeline Health and Data Quality KPIs")
latest = dq_df.iloc[0] if not dq_df.empty else None
c1, c2, c3, c4, c5, c6 = st.columns(6)
if latest is not None:
    c1.metric("Pipeline Status", str(latest["status"]))
    c2.metric("Records Processed", f"{int(latest['total_records']):,}")
    c3.metric("Valid Records", f"{int(latest['valid_records']):,}")
    c4.metric("Rejected Records", f"{int(latest['rejected_records']):,}")
    c5.metric("Data Quality Score", f"{latest['quality_score']:.2f}%")
    c6.metric("Duplicates / Missing", f"{int(latest['duplicate_records'])} / {int(latest['missing_value_records'])}")

st.divider()
st.subheader("Sales and Inventory Performance")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Net Revenue", f"${filtered['net_amount'].sum():,.2f}")
k2.metric("Total Orders", f"{len(filtered):,}")
k3.metric("Units Sold", f"{int(filtered['quantity'].sum()):,}")
k4.metric("Low-Stock SKUs", f"{int(inv_df['needs_reorder'].sum()):,}")

left_col, right_col = st.columns(2)
with left_col:
    st.markdown("**Daily Net Revenue Trend**")
    st.line_chart(filtered.groupby("sale_date")["net_amount"].sum())
with right_col:
    st.markdown("**Net Revenue by Product Category**")
    st.bar_chart(filtered.groupby("category")["net_amount"].sum().sort_values(ascending=False))

st.divider()
t1, t2, t3 = st.tabs(["Data Quality Audit Logs", "Quarantined Records", "Inventory Reorder Exceptions"])
with t1:
    st.dataframe(dq_df, use_container_width=True)
with t2:
    if rejected_df.empty:
        st.success("0 rejected or anomalous records in quarantine.")
    else:
        st.dataframe(rejected_df, use_container_width=True)
with t3:
    st.dataframe(inv_df[inv_df["needs_reorder"] == 1].head(250), use_container_width=True)
