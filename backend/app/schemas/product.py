from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.category import CategoryOut


class ProductImageOut(BaseModel):
    id: int
    url: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ProductVariantOut(BaseModel):
    id: int
    size: str
    color: str
    sku: str
    stock: int
    low_stock_threshold: int

    model_config = ConfigDict(from_attributes=True)


class ProductVariantIn(BaseModel):
    size: str = Field(min_length=1, max_length=20)
    color: str = Field(default="Black", min_length=1, max_length=40)
    sku: str = Field(min_length=1, max_length=80)
    stock: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(
        default=5, ge=0, le=100000
    )

    model_config = ConfigDict(extra="forbid")


class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    price: int
    is_active: bool
    category: CategoryOut | None
    images: list[ProductImageOut]
    variants: list[ProductVariantOut]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def image(self) -> str:
        """Primary image URL, kept for the storefront's existing contract."""
        return self.images[0].url if self.images else ""


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    price: int = Field(ge=0)
    category_id: int | None = None
    is_active: bool = True
    images: list[str] = Field(default_factory=list, max_length=10)
    variants: list[ProductVariantIn] = Field(default_factory=list, max_length=50)

    model_config = ConfigDict(extra="forbid")


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    price: int | None = Field(default=None, ge=0)
    category_id: int | None = None
    is_active: bool | None = None
    images: list[str] | None = Field(default=None, max_length=10)
    variants: list[ProductVariantIn] | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")
