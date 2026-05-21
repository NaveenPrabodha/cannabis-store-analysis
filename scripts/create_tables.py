import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "cannabis_analysis",
    "user": "postgres",
    "password": "admin"
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# ─────────────────────────────────────────────
# DROP TABLES (DEV RESET)
# ─────────────────────────────────────────────

cur.execute("""
DROP TABLE IF EXISTS fct_prices;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_stores;
""")

# ─────────────────────────────────────────────
# DIM STORES
# ─────────────────────────────────────────────

cur.execute("""
CREATE TABLE dim_stores (
    store_id SERIAL PRIMARY KEY,

    store_name TEXT,
    normalized_store_name TEXT,

    address TEXT,
    phone TEXT,

    hibuddy_store_id TEXT,
    hibuddy_slug TEXT
);
""")

# ─────────────────────────────────────────────
# DIM PRODUCTS (FIXED NUMERIC TYPES)
# ─────────────────────────────────────────────

cur.execute("""
CREATE TABLE dim_products (

    product_id BIGINT PRIMARY KEY,

    name TEXT,
    normalized_name TEXT,

    brand TEXT,
    normalized_brand TEXT,

    category TEXT,
    subcategory TEXT,

    size TEXT,

    price NUMERIC(10,2),

    thc_min NUMERIC(10,2),
    thc_max NUMERIC(10,2),

    cbd_min NUMERIC(10,2),
    cbd_max NUMERIC(10,2)
);
""")

# ─────────────────────────────────────────────
# FACT TABLE (FIXED NUMERIC TYPES)
# ─────────────────────────────────────────────

cur.execute("""
CREATE TABLE fct_prices (

    fact_id BIGSERIAL PRIMARY KEY,

    store_id INTEGER REFERENCES dim_stores(store_id),

    product_id BIGINT REFERENCES dim_products(product_id),

    scraped_date DATE,

    regular_price NUMERIC(10,2),
    sale_price NUMERIC(10,2),

    discount_percent NUMERIC(10,2),

    typical_nearby NUMERIC(10,2),

    in_stock BOOLEAN
);
""")

conn.commit()
cur.close()
conn.close()

print("Tables created successfully.")