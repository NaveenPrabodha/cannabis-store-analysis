import os
import re
import pandas as pd
from rapidfuzz import fuzz, process

# ── Paths ─────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

OCS_FILE = os.path.join(BASE_DIR, "output", "clean", "clean_products.csv")
HIBUDDY_FILE = os.path.join(BASE_DIR, "output", "clean", "clean_prices.csv")

MATCH_FILE = os.path.join(BASE_DIR, "output", "clean", "product_matches.csv")
FINAL_FILE = os.path.join(BASE_DIR, "output", "clean", "product_matches_final.csv")


# ── Normalize text ────────────────────────────────────────────

def normalize_text(text):
    if pd.isna(text):
        return ""

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\b\d+(\.\d+)?\s?(g|mg|ml|pk|x)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ── Load data ────────────────────────────────────────────────

print("\nLoading datasets...")

ocs_df = pd.read_csv(OCS_FILE)
hibuddy_df = pd.read_csv(HIBUDDY_FILE)

print(f"OCS products:     {len(ocs_df)}")
print(f"HiBuddy products: {len(hibuddy_df)}")


# ── Normalize ────────────────────────────────────────────────

ocs_df["normalized_name"] = ocs_df["name"].apply(normalize_text)
hibuddy_df["normalized_name"] = hibuddy_df["name"].apply(normalize_text)


# ── Deduplicate OCS ──────────────────────────────────────────

ocs_unique = ocs_df.drop_duplicates(subset=["normalized_name"]).copy()

ocs_lookup_name = dict(zip(
    ocs_unique["normalized_name"],
    ocs_unique["name"]
))

ocs_names = list(ocs_lookup_name.keys())

print(f"Unique OCS names: {len(ocs_names)}")


# ── STEP 1: FUZZY MATCHING ───────────────────────────────────

print("\nMatching products...")

matches = []

for _, row in hibuddy_df.iterrows():

    hibuddy_name = row["name"]
    normalized = row["normalized_name"]

    if not normalized:
        continue

    result = process.extractOne(
        normalized,
        ocs_names,
        scorer=fuzz.ratio
    )

    if not result:
        continue

    matched_key, score, _ = result

    if score < 80:
        continue

    matched_key, score, _ = result
    matched_name = ocs_lookup_name.get(matched_key)

    matches.append({
        "hibuddy_product_id": row.get("hibuddy_product_id", ""),
        "hibuddy_name": hibuddy_name,
        "normalized_hibuddy_name": normalized,
        "matched_ocs_key": matched_key,
        "matched_ocs_name": matched_name,
        "match_score": score
    })

matches_df = pd.DataFrame(matches)

matches_df = matches_df.sort_values(by="match_score", ascending=False)

matches_df.to_csv(MATCH_FILE, index=False)

print(f"\nStep 1 DONE → {len(matches_df)} matches saved")


# ── STEP 2: ATTACH PRODUCT IDs ───────────────────────────────

print("\nAttaching product IDs...")

products_lookup = dict(
    zip(
        ocs_df["normalized_name"].str.lower().str.strip(),
        ocs_df["ocs_product_id"]
    )
)

final_rows = []
missing = 0

for _, row in matches_df.iterrows():

    matched_name = str(row["matched_ocs_name"]).strip().lower()

    product_id = products_lookup.get(matched_name)

    if pd.isna(product_id) or product_id is None:
        missing += 1
        continue

    final_rows.append({
        "hibuddy_product_id": row["hibuddy_product_id"],
        "product_id": int(product_id),
        "match_score": row["match_score"]
    })

final_df = pd.DataFrame(final_rows)

final_df.to_csv(FINAL_FILE, index=False)


# ── SUMMARY ──────────────────────────────────────────────────

print("\nDONE")
print(f"Final matches: {len(final_df)}")
print(f"Missing:       {missing}")
print(f"Saved:         {FINAL_FILE}")