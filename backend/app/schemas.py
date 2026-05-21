from pydantic import BaseModel
from typing import Optional

class StoreSchema(BaseModel):
    store_id: int
    store_name: str | None = None
    address: str | None = None
    phone: str | None = None

    class Config:
        from_attributes = True


class ProductSchema(BaseModel):
    product_id: int
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    size: str | None = None

    class Config:
        from_attributes = True


class DealSchema(BaseModel):
    product_id: int
    name: str | None = None
    store_name: str | None = None

    regular_price: float | None = None
    sale_price: float | None = None

    class Config:
        from_attributes = True