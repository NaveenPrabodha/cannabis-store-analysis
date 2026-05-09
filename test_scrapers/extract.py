import requests
import pandas as pd
import time

BASE_URL = "https://ocs.ca/products.json"

all_products = []
page = 1

while True:
    url = f"{BASE_URL}?limit=250&page={page}"

    print(f"Fetching page {page}")

    response = requests.get(url)

    if response.status_code != 200:
        print("Error:", response.status_code)
        break

    data = response.json()

    products = data.get("products", [])

    if not products:
        print("No more products")
        break

    all_products.extend(products)

    page += 1
    time.sleep(1)

print(f"Total products fetched: {len(all_products)}")