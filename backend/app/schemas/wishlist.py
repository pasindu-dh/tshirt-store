from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductOut


class WishlistItemCreate(BaseModel):
    product_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class WishlistItemOut(BaseModel):
    id: int
    product_id: int
    created_at: datetime
    product: ProductOut

    model_config = ConfigDict(from_attributes=True)
