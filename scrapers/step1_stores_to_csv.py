"""
step1_stores_to_csv.py
----------------------
Writes all 27 Burlington stores to output/stores.csv.
No scraping needed — data was extracted directly from hibuddy.ca/stores/on/burlington.

Fixes vs your current hibuddy_stores.csv:
  - address now includes full street  (was just "BURLINGTON, ON")
  - phone now populated for all stores (was NaN for all 27)
  - added website column

Output columns:
  hibuddy_store_id | hibuddy_slug | name | address | phone | website | city | province

Run: python scrapers/step1_stores_to_csv.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from stores_data import BURLINGTON_STORES

OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'output')
OUT_FILE = os.path.join(OUT_DIR, 'stores.csv')

COLUMNS = [
    'hibuddy_store_id',
    'hibuddy_slug',
    'name',
    'address',
    'phone',
    'website',
    'city',
    'province',
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    skipped = 0

    for store in BURLINGTON_STORES:
        if not store['hibuddy_store_id']:
            print(f"  SKIP (no HiBuddy ID): {store['name']}")
            skipped += 1
            continue

        rows.append({
            'hibuddy_store_id': store['hibuddy_store_id'],
            'hibuddy_slug':     store['hibuddy_slug'],
            'name':             store['name'],
            'address':          store['address'],   # full street e.g. "1220 BRANT ST UNIT 3B, BURLINGTON, ON"
            'phone':            store.get('phone', ''),
            'website':          store.get('website', ''),
            'city':             'Burlington',
            'province':         'ON',
        })
        print(f"  ✓ {store['name']:40s} | {store['address']}")

    with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} stores → {OUT_FILE}")
    if skipped:
        print(f"Skipped {skipped} stores (no HiBuddy ID)")

    # Quick sanity checks
    print("\n--- Sanity check ---")
    print(f"Total stores:   {len(rows)} (expect 26 with IDs + 1 skipped)")
    missing_phone = [r['name'] for r in rows if not r['phone']]
    missing_addr  = [r['name'] for r in rows if 'BURLINGTON, ON' == r['address'].strip()]
    if missing_phone:
        print(f"WARNING — missing phone: {missing_phone}")
    else:
        print("Phones:         ✓ all present")
    if missing_addr:
        print(f"WARNING — no street in address: {missing_addr}")
    else:
        print("Addresses:      ✓ all have street")


if __name__ == '__main__':
    print("=== Step 1: Stores to CSV ===")
    main()