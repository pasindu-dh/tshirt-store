from datetime import date

from pydantic import BaseModel


class ProductPerformanceOut(BaseModel):
    product_id: int | None
    product_name: str
    product_slug: str
    category_id: int | None
    category_name: str
    units_sold: int
    order_count: int
    gross_revenue: int
    returned_units: int
    return_rate: float
    current_stock: int
    stock_value: int
    low_stock_variants: int


class CategoryPerformanceOut(BaseModel):
    category_id: int | None
    category_name: str
    product_count: int
    units_sold: int
    gross_revenue: int


class ProductPerformanceSummaryOut(BaseModel):
    units_sold: int
    gross_revenue: int
    returned_units: int
    return_rate: float
    products_sold: int
    current_stock_value: int
    low_stock_variants: int
    out_of_stock_variants: int


class ProductPerformanceReportOut(BaseModel):
    date_from: date | None
    date_to: date | None
    summary: ProductPerformanceSummaryOut
    products: list[ProductPerformanceOut]
    categories: list[CategoryPerformanceOut]
