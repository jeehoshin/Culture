import hmac
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.fixtures import fixture_events
from app.models import Category, Event, EventList, PriceType
from app.repository import SupabaseRepository
from app.services import filter_events, sort_events
from app.sync import sync_manager

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
    configured = bool(settings.supabase_url and settings.supabase_server_key)
    if settings.use_fixture_data:
        data_mode = "fixtures"
    elif configured:
        data_mode = "supabase"
    else:
        data_mode = "misconfigured"
    return {"status": "ok", "data_mode": data_mode}


def _repository() -> SupabaseRepository:
    if not settings.supabase_url or not settings.supabase_server_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase server settings are not configured.",
        )
    return SupabaseRepository(
        settings.supabase_url,
        settings.supabase_server_key,
        settings.supabase_fetch_limit,
    )


async def _all_events() -> list[Event]:
    if settings.use_fixture_data:
        return fixture_events()
    repository = _repository()
    try:
        return await repository.list_events()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await repository.aclose()


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
    events = await _all_events()
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
        last_synced_at=(
            max(event.updated_at for event in events)
            if events
            else datetime.now(UTC)
        ),
    )


@app.get("/api/v1/events/{event_id}", response_model=Event)
async def event_detail(event_id: str) -> Event:
    if settings.use_fixture_data:
        event = next((item for item in fixture_events() if item.id == event_id), None)
    else:
        repository = _repository()
        try:
            event = await repository.get_event(event_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            await repository.aclose()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.post("/api/v1/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_events(
    background_tasks: BackgroundTasks,
    x_sync_secret: Annotated[str | None, Header()] = None,
    source: Literal["all", "kopis", "culture_portal", "seoul"] = "all",
) -> dict[str, str]:
    if settings.sync_secret == "change-me":
        raise HTTPException(status_code=503, detail="SYNC_SECRET must be changed before syncing.")
    if not x_sync_secret or not hmac.compare_digest(x_sync_secret, settings.sync_secret):
        raise HTTPException(status_code=401, detail="Invalid sync secret.")
    if not settings.supabase_url or not settings.supabase_server_key:
        raise HTTPException(status_code=503, detail="Supabase server settings are not configured.")
    if sync_manager.state["status"] == "running":
        raise HTTPException(status_code=409, detail="A sync is already running.")
    sync_settings = settings.model_copy(
        update={
            "sync_kopis_enabled": source in {"all", "kopis"},
            "sync_culture_portal_enabled": source in {"all", "culture_portal"},
            "sync_seoul_enabled": source in {"all", "seoul"},
        }
    )
    background_tasks.add_task(sync_manager.run, sync_settings)
    return {"status": "accepted"}


@app.post("/api/v1/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_public_data(
    background_tasks: BackgroundTasks,
    scope: Literal["all", "exhibition"] = "all",
) -> dict:
    """Start a rate-limited refresh without exposing the server sync secret."""
    if settings.use_fixture_data:
        raise HTTPException(status_code=503, detail="Refresh is unavailable in fixture mode.")
    if sync_manager.state["status"] == "running":
        return {"status": "running", "sources": list(sync_manager.state.get("sources", {}))}

    requested = ["seoul"] if scope == "exhibition" else ["seoul", "kopis"]
    cutoff = datetime.now(UTC) - timedelta(hours=settings.public_refresh_min_hours)
    repository = _repository()
    try:
        latest = {
            source: await repository.latest_successful_sync(source)
            for source in requested
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await repository.aclose()

    stale = [source for source, finished_at in latest.items() if not finished_at or finished_at < cutoff]
    if not stale:
        return {"status": "up_to_date", "sources": requested}

    refresh_settings = settings.model_copy(
        update={
            "sync_kopis_enabled": "kopis" in stale,
            "sync_culture_portal_enabled": False,
            "sync_seoul_enabled": "seoul" in stale,
        }
    )
    background_tasks.add_task(sync_manager.run, refresh_settings)
    return {"status": "accepted", "sources": stale}


@app.get("/api/v1/sync/status")
async def sync_status() -> dict:
    state = dict(sync_manager.state)
    if settings.use_fixture_data or not settings.supabase_url or not settings.supabase_server_key:
        return state
    repository = _repository()
    try:
        state["latest_runs"] = await repository.latest_sync_runs()
    except RuntimeError as exc:
        state["history_warning"] = str(exc)
    finally:
        await repository.aclose()
    return state
