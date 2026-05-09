"""
step3_hibuddy_prices_to_csv.py
-------------------------------
Scrapes every Burlington store menu on HiBuddy and writes to output/hibuddy_prices.csv.

Fixes vs your current hibuddy_prices.csv:
  1. sale_price column added     — was missing entirely
  2. discount_percent column added — was missing entirely
  3. regular_price renamed correctly:
       your CSV:  regular_price = the "From" price (which is actually the SALE price)
       this CSV:  regular_price = typical_nearby (the real market price)
                  sale_price    = the "From" price when it's lower than typical_nearby
  4. Load-more bug fixed: now clicks until ALL products load before extracting
     (your CSV had 12 unique products × 102 duplicates = 1,224 rows instead of ~459 unique)
  5. Deduplication: skips repeated product IDs on same page

Output columns:
  scraped_date | store_name | hibuddy_store_id | hibuddy_product_id |
  name | brand | category | size | image_url |
  regular_price | sale_price | discount_percent | typical_nearby | in_stock

Test one store first:
  python scrapers/step3_hibuddy_prices_to_csv.py --store-id 5c04f28e66a4e58a346a25970fc2ae2d

Run all stores (~45 mins):
  python scrapers/step3_hibuddy_prices_to_csv.py
"""

import re
import csv
import sys
import time
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from stores_data import BURLINGTON_STORES

OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'output')
OUT_FILE = os.path.join(OUT_DIR, 'hibuddy_prices.csv')

HIBUDDY_BASE = "https://hibuddy.ca"
STORE_DELAY  = 4    # seconds between stores

COLUMNS = [
    'scraped_date',
    'store_name',
    'hibuddy_store_id',
    'hibuddy_product_id',
    'name',
    'brand',
    'category',
    'size',
    'image_url',
    'regular_price',     # = typical_nearby (the real market price)
    'sale_price',        # = "From" price when discounted, else blank
    'discount_percent',  # e.g. 26 (blank when not on sale)
    'typical_nearby',    # raw typical_nearby value from HiBuddy
    'in_stock',
]


# ── Scraping ───────────────────────────────────────────────────────────────

def scrape_store(hibuddy_store_id: str, slug: str, store_name: str) -> list:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    url   = f"{HIBUDDY_BASE}/store/{hibuddy_store_id}/{slug}"
    today = str(date.today())
    rows  = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )).new_page()

        print(f"    Loading {url} ...")
        try:
            page.goto(url, wait_until="networkidle", timeout=30_000)
        except PWTimeout:
            print(f"    TIMEOUT — skipping {store_name}")
            browser.close()
            return []

        # Wait for at least one product link
        try:
            page.wait_for_selector("a[href*='/product/']", timeout=15_000)
        except PWTimeout:
            print(f"    No product links found — skipping {store_name}")
            browser.close()
            return []

        # ── Click "Load more" until all products are loaded ───────────────
        # HiBuddy loads 12 products at a time.
        # We must finish all clicks BEFORE extracting cards.
        clicks = 0
        while True:
            btn = page.locator("button:has-text('Load more')")
            if btn.count() == 0:
                break
            try:
                btn.first.scroll_into_view_if_needed()
                btn.first.click()
                page.wait_for_timeout(700)
                clicks += 1
            except Exception:
                break

        if clicks:
            print(f"    Clicked 'Load more' {clicks}x")

        # ── Extract cards (deduplicated by hibuddy_product_id) ────────────
        seen_ids = set()
        cards    = page.locator("a[href*='/product/']").all()
        print(f"    Found {len(cards)} product links")

        for card in cards:
            try:
                row = parse_card(card, today, store_name, hibuddy_store_id)
                if not row:
                    continue
                pid = row['hibuddy_product_id']
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                rows.append(row)
            except Exception as e:
                pass

        browser.close()

    return rows


def parse_card(card, today: str, store_name: str, hibuddy_store_id: str) -> dict | None:
    """
    Parse one product card <a> element from HiBuddy store menu.

    Card text order (from live site inspection):
      "26% OFF"                          ← discount badge (only when on sale)
      [image]
      "SAN RAFAEL '71•Edibles"           ← brand•category (bullet = U+2022)
      "Blaspberry"                       ← product name
      "4x4.3g"                           ← size
      "From$4.45Typical nearby $6.00"    ← price text

    Product ID extracted from href:
      /product/4adfa1b69fb67aea7017a71917e62365?dealStoreId=...

    Image URL pattern:
      https://hibuddy.ca/assets/pics/{hibuddy_product_id}.jpg
    """
    href = card.get_attribute("href") or ""
    m    = re.search(r'/product/([a-f0-9]+)', href)
    if not m:
        return None
    hibuddy_product_id = m.group(1)

    # Image URL is always the same pattern based on product ID
    image_url = f"https://hibuddy.ca/assets/pics/{hibuddy_product_id}.jpg"

    # Parse card text line by line
    full_text = card.inner_text()
    lines     = [l.strip() for l in full_text.split('\n') if l.strip()]
    if not lines:
        return None

    # Discount badge
    discount_percent = None
    idx = 0
    if re.match(r'^\d+%\s*OFF$', lines[0], re.I):
        m2 = re.search(r'(\d+)', lines[0])
        discount_percent = int(m2.group(1)) if m2 else None
        idx = 1

    # Brand • category
    brand = category = ''
    for i, line in enumerate(lines[idx:], start=idx):
        if '•' in line:
            parts    = line.split('•', 1)
            brand    = parts[0].strip()
            category = parts[1].strip()
            idx      = i + 1
            break

    # Product name
    name = lines[idx] if idx < len(lines) else ''
    idx += 1

    # Size
    size = lines[idx] if idx < len(lines) else ''
    idx += 1

    # Price text: "From$4.45Typical nearby $6.00" or "From$6.25"
    price_text     = ' '.join(lines[idx:])
    from_price     = None
    typical_nearby = None

    from_m = re.search(r'From\s*\$?(\d+\.\d{2})', price_text, re.I)
    if from_m:
        from_price = float(from_m.group(1))

    typ_m = re.search(r'Typical nearby\s*\$?(\d+\.\d{2})', price_text, re.I)
    if typ_m:
        typical_nearby = float(typ_m.group(1))

    if not name or from_price is None:
        return None

    # ── Assign regular_price vs sale_price ────────────────────────────────
    # typical_nearby = normal market price = regular_price in our DB
    # from_price     = what this store charges
    # If from_price < typical_nearby → product is on sale at this store
    if typical_nearby and from_price < typical_nearby:
        regular_price = typical_nearby
        sale_price    = from_price
        # Recalculate discount if badge was absent
        if discount_percent is None:
            discount_percent = round((1 - from_price / typical_nearby) * 100)
    else:
        # Not on sale — from_price IS the regular price
        regular_price    = from_price
        sale_price       = ''
        discount_percent = ''

    return {
        'scraped_date':       today,
        'store_name':         store_name,
        'hibuddy_store_id':   hibuddy_store_id,
        'hibuddy_product_id': hibuddy_product_id,
        'name':               name,
        'brand':              brand,
        'category':           category,   # HiBuddy category (includes Pre-Rolls)
        'size':               size,
        'image_url':          image_url,
        'regular_price':      regular_price,
        'sale_price':         sale_price,
        'discount_percent':   discount_percent,
        'typical_nearby':     typical_nearby if typical_nearby else '',
        'in_stock':           True,
    }


# ── Main ───────────────────────────────────────────────────────────────────

def main(target_id=None):
    os.makedirs(OUT_DIR, exist_ok=True)

    # Filter stores
    stores = [s for s in BURLINGTON_STORES if s['hibuddy_store_id']]
    if target_id:
        stores = [s for s in stores if s['hibuddy_store_id'] == target_id]
        if not stores:
            print(f"ERROR: store ID '{target_id}' not found in stores_data.py")
            sys.exit(1)

    all_rows = []
    total_on_sale = 0

    for store in stores:
        print(f"\n[{stores.index(store)+1}/{len(stores)}] {store['name']}")
        rows = scrape_store(
            store['hibuddy_store_id'],
            store['hibuddy_slug'],
            store['name'],
        )

        if not rows:
            print(f"    WARNING: no products scraped")
            time.sleep(STORE_DELAY)
            continue

        on_sale = sum(1 for r in rows if r['sale_price'] != '')
        total_on_sale += on_sale
        all_rows.extend(rows)
        print(f"    Extracted: {len(rows)} unique products | On sale: {on_sale}")
        time.sleep(STORE_DELAY)

    # Write CSV (append if file exists and we ran single-store mode)
    if target_id and os.path.exists(OUT_FILE):
        mode = 'a'
        write_header = False
        print(f"\nAppending to existing {OUT_FILE}")
    else:
        mode = 'w'
        write_header = True

    with open(OUT_FILE, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{'='*50}")
    print(f"Wrote {len(all_rows)} rows → {OUT_FILE}")
    print(f"On sale: {total_on_sale} / {len(all_rows)}")

    # Sanity checks
    print("\n--- Sanity check ---")
    stores_covered = len(set(r['store_name'] for r in all_rows))
    products_total = len(all_rows)
    print(f"Stores scraped:    {stores_covered}")
    print(f"Total price rows:  {products_total}")

    cats = {}
    for r in all_rows:
        cats[r['category']] = cats.get(r['category'], 0) + 1
    print("Categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat or '(blank)':20s} {count}")

    missing_sale = sum(1 for r in all_rows if r['sale_price'] == '' and r['discount_percent'] == '')
    with_sale    = sum(1 for r in all_rows if r['sale_price'] != '')
    print(f"With sale_price:   {with_sale}")
    print(f"Regular price only:{missing_sale}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--store-id', default=None,
        help=(
            "Scrape one store only (for testing). "
            "Mont Kailash example: --store-id 5c04f28e66a4e58a346a25970fc2ae2d"
        )
    )
    args = parser.parse_args()
    print("=== Step 3: HiBuddy Prices to CSV ===")
    main(args.store_id)