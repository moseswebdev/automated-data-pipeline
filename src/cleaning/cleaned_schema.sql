CREATE TABLE IF NOT EXISTS cleaned_sales (
    transaction_id VARCHAR(50) PRIMARY KEY,
    transaction_timestamp TIMESTAMP NOT NULL,
    sale_date DATE NOT NULL,
    sale_year INTEGER NOT NULL,
    sale_month INTEGER NOT NULL,
    day_of_week VARCHAR(15) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    store_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    gross_amount DECIMAL(12, 2) NOT NULL,
    discount_rate DECIMAL(5, 4) NOT NULL,
    discount_amount DECIMAL(12, 2) NOT NULL,
    net_amount DECIMAL(12, 2) NOT NULL,
    processed_at TIMESTAMP NOT NULL
);
