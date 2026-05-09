"""
step2_ocs_to_csv.py
-------------------
Fetches all products from OCS Shopify API and writes to output/ocs_products.csv.

Fixes vs your current ocs_products.csv:
  - THC/CBD now parsed from tags array (e.g. "THC:10", "CBD:0") AND body_html
  - Your old CSV had THC for only 26 / 10,010 rows — this should be much higher

Output columns match your existing ocs_products.csv exactly:
  ocs_product_id | handle | name | brand | category | description |
  thc_min | thc_max | cbd_min | cbd_max | image_url |
  variant_title | weight_g | sku | price

Run: python scrapers/step2_ocs_to_csv.py
"""

import re
import csv
import sys
import time
import os
import requests

OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'output')
OUT_FILE = os.path.join(OUT_DIR, 'ocs_products.csv')

OCS_BASE   = "https://ocs.ca"
PAGE_DELAY = 0.5   # seconds between pages

COLUMNS = [
    'ocs_product_id', 'handle', 'name', 'brand', 'category',
    'description', 'thc_min', 'thc_max', 'cbd_min', 'cbd_max',
    'image_url', 'variant_title', 'weight_g', 'sku', 'price',
]


# ── Helpers ────────────────────────────────────────────────────────────────

def strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', ' ', html or '').strip()

# Tags like "THC:10", "THC:10.5", "CBD:0"
THC_TAG_RE  = re.compile(r'^THC:(\d+(?:\.\d+)?)$', re.I)
CBD_TAG_RE  = re.compile(r'^CBD:(\d+(?:\.\d+)?)$', re.I)

# body_html patterns like "THC: 10 - 15%", "THC 10mg"
THC_HTML_RE = re.compile(r'THC[:\s]*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?', re.I)
CBD_HTML_RE = re.compile(r'CBD[:\s]*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?', re.I)


def parse_cannabinoids(body_html: str, tags: list):
    """
    Returns (thc_min, thc_max, cbd_min, cbd_max).
    Checks tags array first (OCS uses "THC:10" format consistently),
    then falls back to body_html regex.
    """
    thc_min = thc_max = cbd_min = cbd_max = None

    for tag in (tags or []):
        t = str(tag).strip()
        m = THC_TAG_RE.match(t)
        if m:
            thc_min = thc_max = float(m.group(1))
        m = CBD_TAG_RE.match(t)
        if m:
            cbd_min = cbd_max = float(m.group(1))

    text = strip_html(body_html)
    if thc_min is None:
        m = THC_HTML_RE.search(text)
        if m:
            thc_min = float(m.group(1))
            thc_max = float(m.group(2)) if m.group(2) else thc_min

    if cbd_min is None:
        m = CBD_HTML_RE.search(text)
        if m:
            cbd_min = float(m.group(1))
            cbd_max = float(m.group(2)) if m.group(2) else cbd_min

    return thc_min, thc_max, cbd_min, cbd_max


def parse_weight_g(size: str):
    s = (size or '').lower()
    m = re.search(r'(\d+(?:\.\d+)?)\s*g\b', s)
    if m:
        return float(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)\s*oz\b', s)
    if m:
        return round(float(m.group(1)) * 28.3495, 2)
    return ''


# ── Fetch ──────────────────────────────────────────────────────────────────

def fetch_all_products() -> list:
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0'
    all_products, page = [], 1

    while True:
        url = f"{OCS_BASE}/products.json?limit=250&page={page}"
        print(f"  Fetching page {page} ...", end=' ', flush=True)
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            batch = r.json().get('products', [])
        except Exception as e:
            print(f"FAILED: {e}")
            break

        if not batch:
            print("done.")
            break

        all_products.extend(batch)
        print(f"got {len(batch)} (total: {len(all_products)})")
        page += 1
        time.sleep(PAGE_DELAY)

    return all_products


# ── Transform + write ──────────────────────────────────────────────────────

def to_csv_rows(raw_products: list) -> list:
    """
    Each OCS product can have multiple variants (sizes).
    We write one CSV row per variant — same as your existing ocs_products.csv.
    """
    rows = []
    thc_found = 0

    for raw in raw_products:
        body_html = raw.get('body_html', '') or ''
        tags      = raw.get('tags', [])
        desc      = strip_html(body_html)

        thc_min, thc_max, cbd_min, cbd_max = parse_cannabinoids(body_html, tags)
        if thc_min is not None:
            thc_found += 1

        images    = raw.get('images', [])
        image_url = images[0]['src'] if images else ''

        for v in raw.get('variants', []):
            size = v.get('title', '')
            try:
                price = float(v.get('price', 0))
            except (ValueError, TypeError):
                price = ''

            rows.append({
                'ocs_product_id': str(raw.get('id', '')),
                'handle':         raw.get('handle', ''),
                'name':           (raw.get('title', '') or '').strip(),
                'brand':          (raw.get('vendor', '') or '').strip(),
                'category':       (raw.get('product_type', '') or '').strip(),
                'description':    desc,
                'thc_min':        thc_min if thc_min is not None else '',
                'thc_max':        thc_max if thc_max is not None else '',
                'cbd_min':        cbd_min if cbd_min is not None else '',
                'cbd_max':        cbd_max if cbd_max is not None else '',
                'image_url':      image_url,
                'variant_title':  size,
                'weight_g':       parse_weight_g(size),
                'sku':            v.get('sku', ''),
                'price':          price,
            })

    return rows, thc_found


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Fetching from OCS API ...")
    raw_products = fetch_all_products()

    if not raw_products:
        print("ERROR: No products returned. Check https://ocs.ca/products.json")
        sys.exit(1)

    print(f"\nTransforming {len(raw_products)} products ...")
    rows, thc_found = to_csv_rows(raw_products)

    with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows → {OUT_FILE}")

    # Sanity checks
    unique_products = len(set(r['ocs_product_id'] for r in rows))
    thc_pct = round(100 * thc_found / max(unique_products, 1))
    print("\n--- Sanity check ---")
    print(f"Unique products:    {unique_products}")
    print(f"Total rows (w/variants): {len(rows)}")
    print(f"THC data present:   {thc_found} / {unique_products} ({thc_pct}%)")

    categories = {}
    for r in rows:
        categories[r['category']] = categories.get(r['category'], 0) + 1
    print("Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat or '(blank)':20s} {count}")

    no_image = sum(1 for r in rows if not r['image_url'])
    print(f"Missing images:     {no_image}")
    print(f"\nNOTE: Pre-Rolls appear as 'Extracts' or 'Flower' in OCS.")
    print(f"      Use HiBuddy's category (step 3) for Pre-Rolls on the frontend.")


if __name__ == '__main__':
    print("=== Step 2: OCS Products to CSV ===")
    main()