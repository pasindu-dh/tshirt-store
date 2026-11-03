from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    variant_id: int
    quantity: int = Field(default=1, ge=1, le=99)

    model_config = ConfigDict(extra="forbid")


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)

    model_config = ConfigDict(extra="forbid")


class CartMergeItem(BaseModel):
    variant_id: int
    quantity: int = Field(ge=1, le=99)

    model_config = ConfigDict(extra="forbid")


class CartMergeRequest(BaseModel):
    items: list[CartMergeItem] = Field(default_factory=list, max_length=50)

    model_config = ConfigDict(extra="forbid")


class CartItemOut(BaseModel):
    id: int
    variant_id: int
    product_id: int
    product_name: str
    product_slug: str
    image: str
    price: int
    size: str
    color: str
    sku: str
    stock: int
    quantity: int
    line_total: int


class CartOut(BaseModel):
    items: list[CartItemOut]
    item_count: int
    subtotal: int
    shipping_fee: int
    total: int
