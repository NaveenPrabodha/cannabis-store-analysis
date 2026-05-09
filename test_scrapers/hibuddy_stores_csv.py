"""
hibuddy_stores_csv.py
---------------------

Scrape Burlington cannabis stores from HiBuddy
and export them into CSV.

Requirements:
    pip install cloudscraper beautifulsoup4

Run:
    python hibuddy_stores_csv.py
"""

import csv
import cloudscraper
from bs4 import BeautifulSoup

# =========================================================
# CONFIG
# =========================================================

URL = "https://hibuddy.ca/stores/on/burlington"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

# =========================================================
# CREATE SCRAPER
# =========================================================

scraper = cloudscraper.create_scraper()

# =========================================================
# FETCH PAGE
# =========================================================

response = scraper.get(
    URL,
    headers=HEADERS,
    timeout=20
)

print("Status Code:", response.status_code)

if response.status_code != 200:
    print("Failed to fetch page.")
    exit()

# =========================================================
# PARSE HTML
# =========================================================

soup = BeautifulSoup(response.text, "html.parser")

stores = []
seen_ids = set()

store_links = soup.find_all(
    "a",
    href=lambda h: h and h.startswith("/store/")
)

# =========================================================
# EXTRACT STORE DATA
# =========================================================

for link in store_links:

    href = link.get("href", "")

    # Example:
    # /store/5c04f28e66a4e58a346a25970fc2ae2d/mont-kailash-cannabis

    parts = href.strip("/").split("/")

    if len(parts) < 3:
        continue

    store_id = parts[1]
    slug = parts[2]

    # Skip duplicates
    if store_id in seen_ids:
        continue

    seen_ids.add(store_id)

    # Store name
    name = link.get_text(strip=True)

    # Skip button links
    if name.lower() in (
        "view store",
        "website",
        "directions"
    ):
        continue

    # Find parent section
    section = link.find_parent()

    while section and section.name not in (
        "section",
        "div",
        "article",
        "li"
    ):
        section = section.find_parent()

    address = ""
    phone = ""
    website = ""

    if section:

        # Address
        paras = section.find_all("p")

        if paras:
            address = paras[0].get_text(strip=True)

        # Phone
        tel = section.find(
            "a",
            href=lambda h: h and h.startswith("tel:")
        )

        if tel:
            phone = tel.get_text(strip=True)

        # External website
        ext = section.find(
            "a",
            href=lambda h: (
                h and
                h.startswith("http") and
                "hibuddy" not in h
            )
        )

        if ext:
            website = ext["href"]

    stores.append({
        "hibuddy_store_id": store_id,
        "hibuddy_slug": slug,
        "name": name,
        "address": address,
        "phone": phone,
        "website": website,
        "city": "Burlington",
        "province": "ON"
    })

# =========================================================
# EXPORT CSV
# =========================================================

csv_file = "hibuddy_stores.csv"

with open(
    csv_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "hibuddy_store_id",
            "hibuddy_slug",
            "name",
            "address",
            "phone",
            "website",
            "city",
            "province"
        ]
    )

    writer.writeheader()
    writer.writerows(stores)

# =========================================================
# DONE
# =========================================================

print("Total Stores:", len(stores))
print(f"CSV Saved -> {csv_file}")