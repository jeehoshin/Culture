from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.fixtures import fixture_events
from app.models import Category, Event, EventList, PriceType
from app.services import filter_events, sort_events

settings = get_settings()
app = FastAPI(title="Seoul Culture Finder API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Sync-Secret"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "data_mode": "fixtures" if settings.use_fixture_data else "supabase"}


@app.get("/api/v1/events", response_model=EventList)
async def list_events(
    q: str | None = None,
    category: Annotated[list[Category] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    district: Annotated[list[str] | None, Query()] = None,
    price: PriceType | None = None,
    quick: Annotated[str | None, Query(pattern="^(today|weekend|ending-soon)$")] = None,
    sort: Annotated[str, Query(pattern="^(end_date|price|recent)$")] = "end_date",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
) -> EventList:
    events = fixture_events()
    filtered = filter_events(
        events,
        query=q,
        categories=set(category or []),
        date_from=date_from,
        date_to=date_to,
        districts=set(district or []),
        price_type=price,
        quick=quick,
    )
    ordered = sort_events(filtered, sort)
    start = (page - 1) * page_size
    return EventList(
        items=ordered[start : start + page_size],
        total=len(ordered),
        page=page,
        page_size=page_size,
        last_synced_at=max(event.updated_at for event in events),
    )


@app.get("/api/v1/events/{event_id}", response_model=Event)
async def event_detail(event_id: str) -> Event:
    event = next((item for item in fixture_events() if item.id == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.post("/api/v1/sync")
async def sync_events() -> dict[str, str]:
    raise HTTPException(
        status_code=501,
        detail="Configure API keys and Supabase, then connect the tested collectors to the sync worker.",
    )
