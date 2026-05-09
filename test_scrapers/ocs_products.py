"""
ocs_products.py
---------------
Fetches all products from the OCS public Shopify API
and exports them into CSV.

Endpoint:
    https://ocs.ca/products.json?limit=250&page=N

Exports:
    - ocs_products.csv

Requirements:
    pip install requests

Run:
    python ocs_products.py
"""

import re
import csv
import time
import logging
import requests

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger(__name__)

# =========================================================
# CONFIG
# =========================================================

OCS_BASE = "https://ocs.ca"

PAGE_DELAY = 0.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# =========================================================
# PARSING HELPERS
# =========================================================

def strip_html(html: str):

    return re.sub(
        r"<[^>]+>",
        " ",
        html or ""
    ).strip()

THC_RE = re.compile(
    r'THC[:\s]*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?',
    re.I
)

CBD_RE = re.compile(
    r'CBD[:\s]*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?',
    re.I
)

def parse_cannabinoid(text, pattern):

    m = pattern.search(text or "")

    if not m:
        return None, None

    lo = float(m.group(1))

    hi = float(m.group(2)) if m.group(2) else lo

    return lo, hi

def parse_weight_g(size: str):

    s = (size or "").lower()

    m = re.search(r'(\d+(?:\.\d+)?)\s*g\b', s)

    if m:
        return float(m.group(1))

    m = re.search(r'(\d+(?:\.\d+)?)\s*oz\b', s)

    if m:
        return round(float(m.group(1)) * 28.3495, 2)

    return None

# =========================================================
# FETCH PRODUCTS
# =========================================================

def fetch_all_products():

    session = requests.Session()

    session.headers.update(HEADERS)

    all_products = []

    page = 1

    while True:

        url = f"{OCS_BASE}/products.json?limit=250&page={page}"

        log.info(f"Fetching page {page}...")

        try:

            r = session.get(
                url,
                timeout=20
            )

            r.raise_for_status()

            products = r.json().get(
                "products",
                []
            )

        except Exception as e:

            log.error(
                f"Request failed on page {page}: {e}"
            )

            break

        if not products:

            log.info("No more products — done.")

            break

        all_products.extend(products)

        log.info(
            f"Got {len(products)} products "
            f"(total: {len(all_products)})"
        )

        page += 1

        time.sleep(PAGE_DELAY)

    return all_products

# =========================================================
# SAVE CSV
# =========================================================

def save_to_csv(
    raw_list,
    filename="ocs_products.csv"
):

    rows = []

    for raw in raw_list:

        desc = strip_html(
            raw.get("body_html", "")
        )

        tags_text = " ".join(
            raw.get("tags", [])
        )

        full_text = desc + " " + tags_text

        thc_min, thc_max = parse_cannabinoid(
            full_text,
            THC_RE
        )

        cbd_min, cbd_max = parse_cannabinoid(
            full_text,
            CBD_RE
        )

        images = raw.get("images", [])

        image_url = (
            images[0]["src"]
            if images else ""
        )

        for v in raw.get("variants", []):

            size = v.get("title", "")

            try:
                price = float(v.get("price", 0))
            except:
                price = None

            rows.append({

                "ocs_product_id":
                    raw.get("id", ""),

                "handle":
                    raw.get("handle", ""),

                "name":
                    raw.get("title", "").strip(),

                "brand":
                    raw.get("vendor", "").strip(),

                "category":
                    raw.get("product_type", "").strip(),

                "description":
                    desc,

                "thc_min":
                    thc_min,

                "thc_max":
                    thc_max,

                "cbd_min":
                    cbd_min,

                "cbd_max":
                    cbd_max,

                "image_url":
                    image_url,

                "variant_title":
                    size,

                "weight_g":
                    parse_weight_g(size),

                "sku":
                    v.get("sku", ""),

                "price":
                    price
            })

    if not rows:

        log.warning("No rows to save.")

        return

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
        )

        writer.writeheader()

        writer.writerows(rows)

    log.info(f"CSV saved -> {filename}")

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    log.info("=== OCS Product Fetcher ===")

    products = fetch_all_products()

    if not products:

        log.error("No products fetched.")

    else:

        save_to_csv(products)

    log.info("Done.")