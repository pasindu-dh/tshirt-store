from pydantic import BaseModel


class CatalogImportRowOut(BaseModel):
    row: int
    action: str
    product_name: str
    product_slug: str
    variant: str
    message: str


class CatalogImportSummaryOut(BaseModel):
    total_rows: int
    valid_rows: int
    error_rows: int
    products_create: int
    products_update: int
    variants_create: int
    variants_update: int


class CatalogImportResultOut(BaseModel):
    dry_run: bool
    valid: bool
    summary: CatalogImportSummaryOut
    rows: list[CatalogImportRowOut]
