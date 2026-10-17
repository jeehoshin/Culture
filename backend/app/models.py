from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class Category(StrEnum):
    EXHIBITION = "exhibition"
    PLAY = "play"
    MUSICAL = "musical"


class PriceType(StrEnum):
    FREE = "free"
    PAID = "paid"
    UNKNOWN = "unknown"


class SourceRef(BaseModel):
    source: str
    source_name: str
    external_url: HttpUrl | None = None
    attribution: str


class Event(BaseModel):
    id: str
    title: str
    category: Category
    venue_name: str
    district: str | None = None
    start_date: date
    end_date: date
    price_type: PriceType = PriceType.UNKNOWN
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    price_text: str | None = None
    description: str | None = None
    booking_url: HttpUrl | None = None
    registered_at: datetime
    updated_at: datetime
    sources: list[SourceRef]


class EventList(BaseModel):
    items: list[Event]
    total: int
    page: int
    page_size: int
    last_synced_at: datetime
