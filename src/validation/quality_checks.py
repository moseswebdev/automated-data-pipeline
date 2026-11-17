"""Data quality validation rules for raw and cleaned retail tables."""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def validate_raw_sales(raw_df: pd.DataFrame, valid_products: set, valid_stores: set) -> pd.DataFrame:
    """Filter out or flag invalid raw transactions and log quality metrics."""
    initial_count = len(raw_df)
    logger.info(f"Starting validation on {initial_count:,} raw_sales rows.")

    df = raw_df.dropna(subset=["transaction_id", "store_id", "product_id", "customer_id", "timestamp"]).copy()
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")

    # Enforce business rules: positive quantity/price, valid discount range, valid foreign keys
    valid_mask = (
        (df["quantity"] > 0)
        & (df["unit_price"] > 0)
        & (df["discount_rate"].between(0.0, 1.0))
        & (df["product_id"].isin(valid_products))
        & (df["store_id"].isin(valid_stores))
    )

    rejected_count = initial_count - int(valid_mask.sum())
    if rejected_count > 0:
        logger.warning(f"Rejected {rejected_count:,} invalid or duplicate rows during validation.")
    else:
        logger.info("All raw_sales rows passed business rule validation.")

    return df.loc[valid_mask].copy()


def validate_cleaned_sales(cleaned_df: pd.DataFrame) -> None:
    """Assert post-transformation invariants before loading into cleaned_sales."""
    if cleaned_df.empty:
        raise ValueError("Validation failed: cleaned_sales DataFrame is empty.")
    if cleaned_df.isnull().any().any():
        null_cols = cleaned_df.columns[cleaned_df.isnull().any()].tolist()
        raise ValueError(f"Validation failed: unexpected nulls found in columns {null_cols}")
    if (cleaned_df["net_amount"] < 0).any():
        raise ValueError("Validation failed: negative net_amount values detected.")

    logger.info(f"Post-cleaning assertions passed for {len(cleaned_df):,} records.")
