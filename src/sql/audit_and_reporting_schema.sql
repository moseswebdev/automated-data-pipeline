CREATE TABLE IF NOT EXISTS rejected_sales (
    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50),
    timestamp VARCHAR(50),
    store_id VARCHAR(50),
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    quantity INTEGER,
    unit_price DECIMAL(10, 2),
    discount_rate DECIMAL(5, 4),
    total_amount DECIMAL(12, 2),
    rejection_reason VARCHAR(255) NOT NULL,
    rejected_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_logs (
    run_id VARCHAR(50) PRIMARY KEY,
    run_timestamp TIMESTAMP NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    total_records INTEGER NOT NULL,
    valid_records INTEGER NOT NULL,
    rejected_records INTEGER NOT NULL,
    duplicate_records INTEGER NOT NULL,
    missing_value_records INTEGER NOT NULL,
    anomaly_records INTEGER NOT NULL,
    quality_score DECIMAL(5, 2) NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting_summary (
    report_date DATE NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    total_transactions INTEGER NOT NULL,
    total_units_sold INTEGER NOT NULL,
    gross_revenue DECIMAL(14, 2) NOT NULL,
    total_discounts DECIMAL(14, 2) NOT NULL,
    net_revenue DECIMAL(14, 2) NOT NULL,
    low_stock_sku_count INTEGER NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (report_date, period_type)
);
