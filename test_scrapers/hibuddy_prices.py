"""
hibuddy_prices.py
-----------------

Scrapes HiBuddy product prices and saves to CSV.

Requirements:
    pip install cloudscraper beautifulsoup4

Run:
    python hibuddy_prices.py
"""

import re
import csv
import time
import logging
import cloudscraper

from datetime import date
from bs4 import BeautifulSoup

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

HIBUDDY_BASE = "https://hibuddy.ca"

STORE_DELAY = 2
PAGE_DELAY = 1

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# =========================================================
# STORE LIST
# =========================================================

STORES = [

    {
        "hibuddy_store_id":
            "5c04f28e66a4e58a346a25970fc2ae2d",

        "hibuddy_slug":
            "mont-kailash-cannabis",

        "name":
            "Mont Kailash Cannabis"
    },

    {
        "hibuddy_store_id":
            "2bf1cdff73a30e73a07a1ccd5d1fb975",

        "hibuddy_slug":
            "canna-cabana",

        "name":
            "Canna Cabana"
    },

    {
        "hibuddy_store_id":
            "e53833692ecbd7c86cb69ef0dadde7d4",

        "hibuddy_slug":
            "value-buds",

        "name":
            "Value Buds"
    }
]

# =========================================================
# PARSE PRODUCT CARD
# =========================================================

def parse_product_card(card):

    try:

        # Product link
        a_tag = card.find(
            "a",
            href=re.compile(r"/product/")
        )

        if not a_tag:
            return None

        href = a_tag["href"]

        # Product ID
        m = re.search(
            r"/product/([a-f0-9]+)",
            href
        )

        if not m:
            return None

        hibuddy_product_id = m.group(1)

        # Product name
        name_tag = card.find(
            "h3",
            class_="hbd-product-name"
        )

        name = (
            name_tag.get_text(strip=True)
            if name_tag else ""
        )

        # Brand
        brand_tag = card.find(
            "span",
            class_="hbd-product-brand"
        )

        brand = (
            brand_tag.get_text(strip=True)
            if brand_tag else ""
        )

        # Category
        category_tag = card.find(
            "span",
            class_="hbd-product-category"
        )

        category = (
            category_tag.get_text(
                " ",
                strip=True
            ).replace("•", "")
            if category_tag else ""
        )

        # Size
        size_tag = card.find(
            "span",
            class_="hbd-product-size-badge"
        )

        size = (
            size_tag.get_text(strip=True)
            if size_tag else ""
        )

        # Image
        img = card.find("img")

        image_url = (
            img["src"]
            if img and img.get("src")
            else ""
        )

        # Price
        price_tag = card.find(
            "span",
            class_="hbd-product-price"
        )

        regular_price = None

        if price_tag:

            pm = re.search(
                r"(\d+(?:\.\d+)?)",
                price_tag.get_text()
            )

            if pm:
                regular_price = float(pm.group(1))

        # Typical nearby
        typical_tag = card.find(
            "span",
            class_="hbd-product-price-reference"
        )

        typical_nearby = None

        if typical_tag:

            tm = re.search(
                r"(\d+(?:\.\d+)?)",
                typical_tag.get_text()
            )

            if tm:
                typical_nearby = float(tm.group(1))

        return {

            "hibuddy_product_id":
                hibuddy_product_id,

            "name":
                name,

            "brand":
                brand,

            "category":
                category,

            "size":
                size,

            "image_url":
                image_url,

            "regular_price":
                regular_price,

            "typical_nearby":
                typical_nearby,

            "in_stock":
                True
        }

    except Exception as e:

        print("Parse error:", e)

        return None

# =========================================================
# SCRAPE STORE
# =========================================================

def scrape_store_menu(
    store_id_hb,
    slug
):

    all_products = []

    scraper = cloudscraper.create_scraper()

    page = 1

    while True:

        url = (
            f"{HIBUDDY_BASE}/store/"
            f"{store_id_hb}/{slug}?page={page}"
        )

        log.info(f"Fetching page {page}: {url}")

        try:

            resp = scraper.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            resp.raise_for_status()

            # Save debug html
            with open(
                "debug_page.html",
                "w",
                encoding="utf-8"
            ) as f:

                f.write(resp.text)

        except Exception as e:

            log.warning(f"Request failed: {e}")

            break

        soup = BeautifulSoup(
            resp.text,
            "html.parser"
        )

        # FIND PRODUCT CARDS
        product_cards = soup.find_all(
            "article",
            class_=lambda c: c and "hbd-product-card" in c
        )

        if not product_cards:

            log.warning(
                "No product cards found"
            )

            break

        page_products = []

        for card in product_cards:

            product = parse_product_card(card)

            if product:
                page_products.append(product)

        all_products.extend(page_products)

        log.info(
            f"Page {page}: "
            f"{len(page_products)} products "
            f"(total: {len(all_products)})"
        )

        # Last page
        if len(page_products) < 12:
            break

        page += 1

        time.sleep(PAGE_DELAY)

    return all_products

# =========================================================
# SAVE CSV
# =========================================================

def save_to_csv(
    rows,
    filename="hibuddy_prices.csv"
):

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

def run():

    all_rows = []

    today = str(date.today())

    for store in STORES:

        log.info(
            f"Store: {store['name']}"
        )

        raw_products = scrape_store_menu(
            store["hibuddy_store_id"],
            store["hibuddy_slug"]
        )

        for raw in raw_products:

            row = {

                "scraped_date":
                    today,

                "store_name":
                    store["name"],

                "hibuddy_store_id":
                    store["hibuddy_store_id"],

                **raw
            }

            all_rows.append(row)

        log.info(
            f"Collected "
            f"{len(raw_products)} products"
        )

        time.sleep(STORE_DELAY)

    save_to_csv(all_rows)

    log.info(
        f"Done. Total rows: {len(all_rows)}"
    )

# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":

    log.info(
        "=== HiBuddy Price Scraper ==="
    )

    run()