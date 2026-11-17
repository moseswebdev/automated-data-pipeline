CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(50) PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    region VARCHAR(50) NOT NULL,
    store_tier VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_sales (
    transaction_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    store_id VARCHAR(50) REFERENCES stores(store_id),
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount_rate DECIMAL(5, 4) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    store_id VARCHAR(50) REFERENCES stores(store_id),
    product_id VARCHAR(50) REFERENCES products(product_id),
    units_sold_12m INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL,
    stock_on_hand INTEGER NOT NULL,
    needs_reorder BOOLEAN NOT NULL,
    last_updated DATE NOT NULL,
    PRIMARY KEY (store_id, product_id)
);
