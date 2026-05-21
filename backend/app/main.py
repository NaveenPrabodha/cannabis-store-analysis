from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import Store, Product, Price

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Cannabis API Running"}


@app.get("/stores")
def get_stores():

    db: Session = SessionLocal()

    stores = db.query(Store).all()

    return stores


@app.get("/stores/{store_id}")
def get_store(store_id: int):

    db: Session = SessionLocal()
    try:
        store = db.query(Store).filter(Store.store_id == store_id).first()

        if not store:
            return {"error": "Store not found"}

        return store
    finally:
        db.close()


@app.get("/products")
def get_products():

    db: Session = SessionLocal()

    products = db.query(Product).limit(50).all()

    return products

@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):

    product = db.query(Product).filter(
        Product.product_id == product_id
    ).first()

    if not product:
        return {"error": "Product not found"}

    prices = db.query(Price).filter(
        Price.product_id == product_id
    ).all()

    stores = []

    for price in prices:

        store = db.query(Store).filter(
            Store.store_id == price.store_id
        ).first()

        stores.append({
            "store_id": store.store_id,
            "store_name": store.store_name,
            "regular_price": float(price.regular_price) if price.regular_price else None,
            "sale_price": float(price.sale_price) if price.sale_price else None,
            "in_stock": price.in_stock
        })

    return {
        "product_id": product.product_id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "size": product.size,
        "stores": stores
    }


@app.get("/deals")
def get_deals():

    db: Session = SessionLocal()

    rows = (
        db.query(
            Product.product_id,
            Product.name,
            Price.regular_price,
            Price.sale_price
        )
        .join(
            Price,
            Product.product_id == Price.product_id
        )
        .filter(Price.sale_price != None)
        .limit(50)
        .all()
    )

    results = []

    for row in rows:

        results.append({
            "product_id": row.product_id,
            "name": row.name,
            "regular_price": float(row.regular_price) if row.regular_price else None,
            "sale_price": float(row.sale_price) if row.sale_price else None,
        })

    return results
    

@app.get("/search")
def search(q: str, db: Session = Depends(get_db)):

    products = db.query(Product).filter(
        Product.name.ilike(f"%{q}%")
    ).all()

    stores = db.query(Store).filter(
        Store.store_name.ilike(f"%{q}%")
    ).all()

    return {
        "products": [
            {
                "product_id": p.product_id,
                "name": p.name,
                "brand": p.brand
            }
            for p in products
        ],

        "stores": [
            {
                "store_id": s.store_id,
                "store_name": s.store_name
            }
            for s in stores
        ]
    }

@app.get("/stores/{store_id}/products")
def get_store_products(store_id: int, db: Session = Depends(get_db)):

    rows = (
        db.query(
            Product.product_id,
            Product.name,
            Product.brand,
            Price.regular_price,
            Price.sale_price
        )
        .join(Price, Product.product_id == Price.product_id)
        .filter(Price.store_id == store_id)
        .limit(100)
        .all()
    )

    results = []

    for row in rows:
        results.append({
            "product_id": row.product_id,
            "name": row.name,
            "brand": row.brand,
            "regular_price": float(row.regular_price) if row.regular_price else None,
            "sale_price": float(row.sale_price) if row.sale_price else None
        })

    return results


@app.get("/products/{product_id}/stores")
def get_product_stores(product_id: int):

    db: Session = SessionLocal()

    try:
        rows = (
            db.query(
                Store.store_name,
                Price.regular_price,
                Price.sale_price
            )
            .join(Store, Price.store_id == Store.store_id)
            .filter(Price.product_id == product_id)
            .all()
        )

        results = []

        for row in rows:
            results.append({
                "store_name": row.store_name,
                "regular_price": float(row.regular_price) if row.regular_price else None,
                "sale_price": float(row.sale_price) if row.sale_price else None
            })

        return results
    finally:
        db.close()