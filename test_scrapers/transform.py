from extract import all_products
import pandas as pd
cleaned = []

for product in all_products:

    title = product.get("title")
    vendor = product.get("vendor")
    product_type = product.get("product_type")
    tags = product.get("tags")

    for variant in product.get("variants", []):

        row = {
            "product_id": product.get("id"),
            "title": title,
            "brand": vendor,
            "category": product_type,
            "tags": tags,
            "variant_id": variant.get("id"),
            "sku": variant.get("sku"),
            "price": variant.get("price"),
            "inventory_quantity": variant.get("inventory_quantity")
        }

        cleaned.append(row)

df = pd.DataFrame(cleaned)

print(df.head())

df.to_csv("ocs_products.csv", index=False)