from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class Product(BaseModel):
    source_id: str
    url: HttpUrl
    sku: Optional[str] = None
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    list_price: Optional[Decimal] = None
    currency: Optional[str] = None
    availability: Optional[
        Literal["in_stock", "out_of_stock", "preorder", "unknown"]
    ] = "unknown"
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    specs: dict[str, str] = Field(default_factory=dict)
    images: list[HttpUrl] = Field(default_factory=list)
    breadcrumbs: list[str] = Field(default_factory=list)
    fetched_at: datetime
    parser_name: str
    parser_confidence: float = Field(ge=0.0, le=1.0)


class IngestionRequest(BaseModel):
    session_id: Optional[str] = None
    url: str
    max_pages: int = Field(default=100, ge=1, le=500)
    max_depth: int = Field(default=2, ge=0, le=3)
    render_js: bool = False


class SourceStatus(BaseModel):
    source_id: str
    url: str
    status: str
    pages_seen: int = 0
    products_indexed: int = 0
    errors: list[dict] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
