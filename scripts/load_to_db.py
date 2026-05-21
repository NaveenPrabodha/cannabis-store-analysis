import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ─────────────────────────────────────────────────────
# DB CONFIG
# ─────────────────────────────────────────────────────

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "cannabis_analysis",
    "user": "postgres",
    "password": "admin"
}

# ─────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CLEAN_DIR = os.path.join(BASE_DIR, "output", "clean")

STORES_FILE = os.path.join(CLEAN_DIR, "clean_stores.csv")
PRODUCTS_FILE = os.path.join(CLEAN_DIR, "clean_products.csv")
PRICES_FILE = os.path.join(CLEAN_DIR, "clean_prices.csv")

# NEW MATCH FILE
MATCH_FILE = os.path.join(CLEAN_DIR, "product_matches_final.csv")
matches = pd.read_csv(MATCH_FILE)

# ─────────────────────────────────────────────────────
# CONNECT
# ─────────────────────────────────────────────────────

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# ─────────────────────────────────────────────────────
# OPTIONAL CLEAN TABLES
# ─────────────────────────────────────────────────────

print("\n=== TRUNCATING TABLES ===")

cur.execute("""
TRUNCATE fct_prices RESTART IDENTITY CASCADE;
TRUNCATE dim_products RESTART IDENTITY CASCADE;
TRUNCATE dim_stores RESTART IDENTITY CASCADE;
""")

conn.commit()

print("Tables truncated.")

# ─────────────────────────────────────────────────────
# LOAD STORES
# ─────────────────────────────────────────────────────

print("\n=== LOADING STORES ===")

stores = pd.read_csv(STORES_FILE)

store_rows = []

for _, row in stores.iterrows():

    store_rows.append((
        row.get("name"),
        row.get("normalized_store_name"),
        row.get("address"),
        row.get("phone"),
        row.get("hibuddy_store_id"),
        row.get("hibuddy_slug"),
    ))

execute_values(
    cur,
    """
    INSERT INTO dim_stores (
        store_name,
        normalized_store_name,
        address,
        phone,
        hibuddy_store_id,
        hibuddy_slug
    )
    VALUES %s
    """,
    store_rows
)

conn.commit()

print(f"Inserted stores: {len(store_rows)}")

# ─────────────────────────────────────────────────────
# LOAD PRODUCTS
# ─────────────────────────────────────────────────────

print("\n=== LOADING PRODUCTS ===")

products = pd.read_csv(PRODUCTS_FILE)

product_rows = []

for _, row in products.iterrows():

    def safe_float(val):

        if pd.isna(val):
            return None

        try:
            val = float(val)

            # remove impossible scraped values
            if val > 999999:
                return None

            return val

        except:
            return None

    product_rows.append((

    int(row.get("ocs_product_id")),

    row.get("name"),
    row.get("normalized_name"),

    row.get("brand"),
    row.get("normalized_brand"),

    row.get("category"),
    row.get("subcategory"),

    row.get("size"),

    safe_float(row.get("price")),

    safe_float(row.get("thc_min")),
    safe_float(row.get("thc_max")),

    safe_float(row.get("cbd_min")),
    safe_float(row.get("cbd_max")),
))

execute_values(
    cur,
    """
    INSERT INTO dim_products (

        product_id,

        name,
        normalized_name,

        brand,
        normalized_brand,

        category,
        subcategory,

        size,

        price,

        thc_min,
        thc_max,

        cbd_min,
        cbd_max
)
VALUES %s
    """,
    product_rows
)

conn.commit()

print(f"Inserted products: {len(product_rows)}")

# ─────────────────────────────────────────────────────
# BUILD LOOKUPS
# ─────────────────────────────────────────────────────

print("\n=== BUILDING LOOKUPS ===")

# STORE LOOKUP
cur.execute("""
SELECT store_id, hibuddy_store_id
FROM dim_stores
""")

store_lookup = {
    row[1]: row[0]
    for row in cur.fetchall()
}

print(f"Store lookup size: {len(store_lookup)}")

# PRODUCT LOOKUP
cur.execute("""
SELECT
    product_id,
    normalized_name,
    normalized_brand
FROM dim_products
""")

product_lookup = {}

for row in cur.fetchall():

    product_id = row[0]
    normalized_name = row[1]
    normalized_brand = row[2]

    key = (
        str(normalized_name).strip().lower(),
        str(normalized_brand).strip().lower()
    )

    product_lookup[key] = product_id

print(f"Product lookup size: {len(product_lookup)}")

# ─────────────────────────────────────────────────────
# LOAD PRODUCT MATCHES
# ─────────────────────────────────────────────────────

print("\n=== LOADING PRODUCT MATCHES ===")

matches = pd.read_csv(MATCH_FILE)

match_lookup = {}

for _, row in matches.iterrows():

    hibuddy_product_id = row["hibuddy_product_id"]
    product_id = row["product_id"]

    match_lookup[hibuddy_product_id] = product_id

print(f"Match lookup size: {len(match_lookup)}")

# ─────────────────────────────────────────────────────
# LOAD FACT PRICES
# ─────────────────────────────────────────────────────

print("\n=== LOADING FACT PRICES ===")

prices = pd.read_csv(PRICES_FILE)

fact_rows = []

missing_store = 0
missing_product = 0

for _, row in prices.iterrows():

    # STORE MATCH
    store_id = store_lookup.get(
        row.get("hibuddy_store_id")
    )

    if not store_id:
        missing_store += 1
        continue

    # PRODUCT MATCH
    hibuddy_product_id = row.get("hibuddy_product_id")

    product_id = match_lookup.get(hibuddy_product_id)

    if pd.isna(product_id):
        missing_product += 1
        continue

    # SAFE NUMBERS
    regular_price = row.get("regular_price")
    sale_price = row.get("sale_price")
    discount_percent = row.get("discount_percent")
    typical_nearby = row.get("typical_nearby")

    fact_rows.append((
        int(store_id),
        int(product_id),

        row.get("scraped_date"),

        regular_price if pd.notna(regular_price) else None,
        sale_price if pd.notna(sale_price) else None,

        discount_percent if pd.notna(discount_percent) else None,

        typical_nearby if pd.notna(typical_nearby) else None,

        bool(row.get("in_stock"))
    ))

# ─────────────────────────────────────────────────────
# INSERT FACTS
# ─────────────────────────────────────────────────────

print(f"Fact rows prepared: {len(fact_rows)}")

if fact_rows:

    execute_values(
        cur,
        """
        INSERT INTO fct_prices (
            store_id,
            product_id,

            scraped_date,

            regular_price,
            sale_price,

            discount_percent,

            typical_nearby,

            in_stock
        )
        VALUES %s
        """,
        fact_rows
    )

    conn.commit()

print(f"Inserted fact rows: {len(fact_rows)}")

# ─────────────────────────────────────────────────────
# FINAL STATS
# ─────────────────────────────────────────────────────

print("\n=== FINAL STATS ===")

print(f"Missing stores:   {missing_store}")
print(f"Missing products: {missing_product}")

# DB COUNTS

cur.execute("SELECT COUNT(*) FROM dim_stores")
print(f"dim_stores:   {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM dim_products")
print(f"dim_products: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM fct_prices")
print(f"fct_prices:   {cur.fetchone()[0]}")

# ─────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────

cur.close()
conn.close()

print("\nETL LOAD COMPLETE")

print(matches.columns.tolist())
print(matches.head())