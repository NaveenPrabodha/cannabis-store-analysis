import os
import re
import pandas as pd
from rapidfuzz import fuzz, process

# ─────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

OCS_FILE = os.path.join(
    BASE_DIR,
    "output",
    "clean",
    "clean_products.csv"
)

HIBUDDY_FILE = os.path.join(
    BASE_DIR,
    "output",
    "clean",
    "clean_prices.csv"
)

FINAL_FILE = os.path.join(
    BASE_DIR,
    "output",
    "clean",
    "product_matches_final.csv"
)

# ─────────────────────────────────────────────────────
# NORMALIZER
# ─────────────────────────────────────────────────────

def normalize_text(text):

    if pd.isna(text):
        return ""

    text = str(text).lower().strip()

    # remove symbols
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # remove weights/sizes
    text = re.sub(
        r"\b\d+(\.\d+)?\s?(g|mg|ml|pk|x)\b",
        " ",
        text
    )

    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text

# ─────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────

print("\nLoading datasets...")

ocs_df = pd.read_csv(OCS_FILE)
hibuddy_df = pd.read_csv(HIBUDDY_FILE)

print(f"OCS products:     {len(ocs_df)}")
print(f"HiBuddy rows:     {len(hibuddy_df)}")

# ─────────────────────────────────────────────────────
# BUILD OCS MATCH STRINGS
# ─────────────────────────────────────────────────────

ocs_df["match_text"] = (
    ocs_df["name"].fillna("").apply(normalize_text)
    + " " +
    ocs_df["brand"].fillna("").apply(normalize_text)
)

# remove duplicates
ocs_df = ocs_df.drop_duplicates(subset=["match_text"])

print(f"Unique OCS products: {len(ocs_df)}")

# ─────────────────────────────────────────────────────
# BUILD LOOKUP
# ─────────────────────────────────────────────────────

ocs_lookup = {}

for _, row in ocs_df.iterrows():

    match_text = row["match_text"]

    ocs_lookup[match_text] = {
        "product_id": row["ocs_product_id"],
        "name": row["name"]
    }

ocs_keys = list(ocs_lookup.keys())

# ─────────────────────────────────────────────────────
# MATCH PRODUCTS
# ─────────────────────────────────────────────────────

print("\nMatching products...")

matches = []

matched_count = 0

for _, row in hibuddy_df.iterrows():

    hibuddy_product_id = row.get("hibuddy_product_id")

    hibuddy_text = (
        normalize_text(row.get("name"))
        + " " +
        normalize_text(row.get("brand"))
    ).strip()

    if not hibuddy_text:
        continue

    result = process.extractOne(
        hibuddy_text,
        ocs_keys,
        scorer=fuzz.token_sort_ratio
    )

    if not result:
        continue

    matched_key, score, _ = result

    # MUCH BETTER THRESHOLD
    if score < 75:
        continue

    matched_product = ocs_lookup[matched_key]

    matches.append({
        "hibuddy_product_id": hibuddy_product_id,
        "product_id": int(matched_product["product_id"]),
        "match_score": score
    })

    matched_count += 1

# ─────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────

matches_df = pd.DataFrame(matches)

# remove duplicates
matches_df = matches_df.drop_duplicates(
    subset=["hibuddy_product_id"]
)

matches_df.to_csv(FINAL_FILE, index=False)

# ─────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────

print("\nDONE")
print(f"Matches created: {len(matches_df)}")
print(f"Saved to:")
print(FINAL_FILE)