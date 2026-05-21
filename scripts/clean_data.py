import os
import re
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

RAW_DIR = os.path.join(BASE_DIR, "output")
CLEAN_DIR = os.path.join(RAW_DIR, "clean")

os.makedirs(CLEAN_DIR, exist_ok=True)

STORES_FILE = os.path.join(RAW_DIR, "stores.csv")
PRODUCTS_FILE = os.path.join(RAW_DIR, "ocs_products.csv")
PRICES_FILE = os.path.join(RAW_DIR, "hibuddy_prices.csv")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def normalize_text(text):
    """
    Normalize text for matching:
    - uppercase
    - remove punctuation
    - collapse spaces
    """
    if pd.isna(text):
        return ""

    text = str(text).upper().strip()

    text = re.sub(r"[^A-Z0-9\s]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_numeric(series):
    """
    Convert numeric columns safely.
    """
    return pd.to_numeric(series, errors="coerce")


# ─────────────────────────────────────────────────────────────
# CLEAN STORES
# ─────────────────────────────────────────────────────────────

print("\n=== CLEANING STORES ===")

stores = pd.read_csv(STORES_FILE)

stores.columns = stores.columns.str.strip()

stores["normalized_store_name"] = (
    stores["name"]
    .fillna("")
    .apply(normalize_text)
)

stores = stores.drop_duplicates(subset=["hibuddy_store_id"])

clean_stores = stores[
    [
        "name",
        "normalized_store_name",
        "address",
        "phone",
        "hibuddy_store_id",
        "hibuddy_slug",
    ]
].copy()

clean_stores.to_csv(
    os.path.join(CLEAN_DIR, "clean_stores.csv"),
    index=False
)

print(f"Stores cleaned: {len(clean_stores)}")


# ─────────────────────────────────────────────────────────────
# CLEAN PRODUCTS
# ─────────────────────────────────────────────────────────────

print("\n=== CLEANING PRODUCTS ===")

products = pd.read_csv(PRODUCTS_FILE)

products.columns = products.columns.str.strip()

# Normalize text
products["normalized_name"] = (
    products["name"]
    .fillna("")
    .apply(normalize_text)
)

products["normalized_brand"] = (
    products["brand"]
    .fillna("")
    .apply(normalize_text)
)

# Standardize categories
products["category"] = (
    products["category"]
    .fillna("UNKNOWN")
    .str.strip()
    .str.title()
)

products["category"] = (
    products["category"]
    .replace({
        "Pre Rolls": "Pre-Rolls",
        "Pre-Roll": "Pre-Rolls",
        "Vape": "Vapes",
    })
)

# Numeric cleanup
numeric_cols = [
    "price",
    "thc_min",
    "thc_max",
    "cbd_min",
    "cbd_max"
]

for col in numeric_cols:
    if col in products.columns:
        products[col] = clean_numeric(products[col])

# Remove duplicates
products = products.drop_duplicates(
    subset=["normalized_name", "normalized_brand"]
)

clean_products = products.copy()

clean_products.to_csv(
    os.path.join(CLEAN_DIR, "clean_products.csv"),
    index=False
)

print(f"Products cleaned: {len(clean_products)}")


# ─────────────────────────────────────────────────────────────
# CLEAN PRICES
# ─────────────────────────────────────────────────────────────

print("\n=== CLEANING PRICES ===")

prices = pd.read_csv(PRICES_FILE)

prices.columns = prices.columns.str.strip()

# Normalize names
prices["normalized_name"] = (
    prices["name"]
    .fillna("")
    .apply(normalize_text)
)

prices["normalized_brand"] = (
    prices["brand"]
    .fillna("")
    .apply(normalize_text)
)

# Numeric cleanup
price_cols = [
    "regular_price",
    "sale_price",
    "discount_percent",
    "typical_nearby",
]

for col in price_cols:
    if col in prices.columns:
        prices[col] = clean_numeric(prices[col])

# Remove duplicate products inside same store
prices = prices.drop_duplicates(
    subset=[
        "store_name",
        "hibuddy_product_id"
    ]
)

# Keep only reliable columns
keep_cols = [
    "scraped_date",
    "store_name",
    "hibuddy_store_id",
    "hibuddy_product_id",
    "name",
    "normalized_name",
    "brand",
    "normalized_brand",
    "regular_price",
    "sale_price",
    "discount_percent",
    "typical_nearby",
    "in_stock",
]

prices = prices[keep_cols]

clean_prices = prices.copy()

clean_prices.to_csv(
    os.path.join(CLEAN_DIR, "clean_prices.csv"),
    index=False
)

print(f"Prices cleaned: {len(clean_prices)}")


# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────

print("\n" + "=" * 60)

print("CLEANING COMPLETE")

print(f"""
Generated files:

{CLEAN_DIR}

- clean_stores.csv
- clean_products.csv
- clean_prices.csv
""")