import re
import csv
import time
import os
import argparse
from datetime import date

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from stores_data import BURLINGTON_STORES

HIBUDDY_BASE = "https://hibuddy.ca"

OUT_DIR = "output"
OUT_FILE = os.path.join(OUT_DIR, "hibuddy_prices.csv")

STORE_DELAY = 5

COLUMNS = [
    "scraped_date",
    "store_name",
    "hibuddy_store_id",
    "hibuddy_product_id",
    "name",
    "brand",
    "category",
    "size",
    "image_url",
    "regular_price",
    "sale_price",
    "discount_percent",
    "typical_nearby",
    "in_stock",
]


def parse_cards(html, store_name, store_id, today):
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.find_all("article")

    rows = []
    seen = set()

    for card in cards:
        try:
            html_text = str(card)

            m = re.search(r"/product/([a-f0-9]+)", html_text)

            if not m:
                continue

            product_id = m.group(1)

            if product_id in seen:
                continue

            seen.add(product_id)

            text = card.get_text("\n", strip=True)

            lines = [x.strip() for x in text.split("\n") if x.strip()]

            h3 = card.find("h3")

            if not h3:
                continue

            name = h3.get_text(strip=True)

            brand = ""
            category = ""

            for line in lines:
                if "•" in line:
                    parts = line.split("•", 1)

                    brand = parts[0].strip()
                    category = parts[1].strip()

                    break

            size = ""

            for line in lines:
                if re.search(r"\d+(\.\d+)?\s?(g|ml|pk|x)", line, re.I):
                    size = line
                    break

            discount_percent = ""

            discount_match = re.search(
                r"(\d+)%\s*OFF",
                text,
                re.I,
            )

            if discount_match:
                discount_percent = int(
                    discount_match.group(1)
                )

            from_price = None

            from_match = re.search(
                r"From\s*\$?(\d+\.\d+)",
                text,
                re.I,
            )

            if from_match:
                from_price = float(
                    from_match.group(1)
                )

            nearby_price = ""

            nearby_match = re.search(
                r"Typical nearby\s*\$?(\d+\.\d+)",
                text,
                re.I,
            )

            if nearby_match:
                nearby_price = float(
                    nearby_match.group(1)
                )

            if from_price is None:
                continue

            if nearby_price and from_price < nearby_price:
                regular_price = nearby_price
                sale_price = from_price
            else:
                regular_price = from_price
                sale_price = ""

            image_url = (
                f"https://hibuddy.ca/assets/pics/"
                f"{product_id}.jpg"
            )

            rows.append(
                {
                    "scraped_date": today,
                    "store_name": store_name,
                    "hibuddy_store_id": store_id,
                    "hibuddy_product_id": product_id,
                    "name": name,
                    "brand": brand,
                    "category": category,
                    "size": size,
                    "image_url": image_url,
                    "regular_price": regular_price,
                    "sale_price": sale_price,
                    "discount_percent": discount_percent,
                    "typical_nearby": nearby_price,
                    "in_stock": True,
                }
            )

        except Exception as e:
            print(f"Parse error: {e}")

    return rows


def scrape_store(store, today):
    url = (
        f"{HIBUDDY_BASE}/store/"
        f"{store['hibuddy_store_id']}/"
        f"{store['hibuddy_slug']}"
    )

    print(f"\nOpening: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,
        )

        context = browser.new_context(
            viewport={
                "width": 1400,
                "height": 1000,
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        Stealth().apply_stealth_sync(page)

        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(3000)

        click_count = 0

        while True:
            try:
                btn = page.locator(
                    "button:has-text('Load more')"
                )

                if btn.count() == 0:
                    break

                btn.first.scroll_into_view_if_needed()

                btn.first.click()

                click_count += 1

                print(
                    f"Clicked Load More: {click_count}"
                )

                page.wait_for_timeout(2500)

            except Exception:
                break

        print("Finished loading all products")

        html = page.content()

        browser.close()

    rows = parse_cards(
        html,
        store["name"],
        store["hibuddy_store_id"],
        today,
    )

    return rows


def main(target_id=None):
    os.makedirs(
        OUT_DIR,
        exist_ok=True,
    )

    # skip stores with missing IDs
    stores = [
        store
        for store in BURLINGTON_STORES
        if store["hibuddy_store_id"]
    ]

    if target_id:
        stores = [
            s
            for s in stores
            if s["hibuddy_store_id"] == target_id
        ]

    today = str(date.today())

    all_rows = []

    for i, store in enumerate(stores, 1):
        print(
            f"\n[{i}/{len(stores)}] "
            f"{store['name']}"
        )

        rows = scrape_store(
            store,
            today,
        )

        print(
            f"Collected: {len(rows)} products"
        )

        all_rows.extend(rows)

        time.sleep(STORE_DELAY)

    with open(
        OUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=COLUMNS,
        )

        writer.writeheader()

        writer.writerows(all_rows)

    print("\nDONE")
    print(f"Rows: {len(all_rows)}")
    print(f"Saved: {OUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--store-id",
        default=None,
    )

    args = parser.parse_args()

    main(args.store_id)