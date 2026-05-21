from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, ForeignKey
from app.database import Base


class Store(Base):
    __tablename__ = "dim_stores"

    store_id = Column(Integer, primary_key=True)
    store_name = Column(String)
    address = Column(String)
    phone = Column(String)


class Product(Base):
    __tablename__ = "dim_products"

    product_id = Column(Integer, primary_key=True)
    name = Column(String)
    brand = Column(String)
    category = Column(String)
    size = Column(String)


class Price(Base):
    __tablename__ = "fct_prices"

    fact_id = Column(Integer, primary_key=True)

    store_id = Column(Integer, ForeignKey("dim_stores.store_id"))
    product_id = Column(Integer, ForeignKey("dim_products.product_id"))

    scraped_date = Column(Date)

    regular_price = Column(Numeric)
    sale_price = Column(Numeric)

    discount_percent = Column(Numeric)

    typical_nearby = Column(Numeric)

    in_stock = Column(Boolean)