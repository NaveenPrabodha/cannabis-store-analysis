import os
import pandas as pd

# ── Config ─────────────────────────────────────────────

MATCH_THRESHOLD = 85

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "output",
    "clean",
    "product_matches.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "output",
    "clean",
    "product_matches_final.csv"
)

LOW_CONF_FILE = os.path.join(
    BASE_DIR,
    "output",
    "clean",
    "low_confidence_matches.csv"
)

# ── Load data ──────────────────────────────────────────

print("\nLoading product matches...")

df = pd.read_csv(INPUT_FILE)

print(f"Total matches: {len(df)}")

# ── Split confidence levels ────────────────────────────

high_conf = df[df["match_score"] >= MATCH_THRESHOLD].copy()

low_conf = df[df["match_score"] < MATCH_THRESHOLD].copy()

# ── Save outputs ───────────────────────────────────────

high_conf.to_csv(OUTPUT_FILE, index=False)

low_conf.to_csv(LOW_CONF_FILE, index=False)

# ── Stats ──────────────────────────────────────────────

print("\nDONE")

print(f"High-confidence matches: {len(high_conf)}")
print(f"Low-confidence matches:  {len(low_conf)}")

print(f"\nSaved:")
print(f"  {OUTPUT_FILE}")
print(f"  {LOW_CONF_FILE}")