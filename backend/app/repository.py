from datetime import UTC, date, datetime

import httpx

from app.models import Category, Event, PriceType, SourceRef


class SupabaseRepository:
    def __init__(self, url: str, server_key: str, fetch_limit: int = 5000):
        self.base_url = f"{url.rstrip('/')}/rest/v1"
        self.fetch_limit = fetch_limit
        headers = {"apikey": server_key, "Content-Type": "application/json"}
        if not server_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {server_key}"
        self.client = httpx.AsyncClient(
            timeout=60,
            headers=headers,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = await self.client.request(method, f"{self.base_url}/{path}", **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase request failed with HTTP {response.status_code}")
        return response

    @staticmethod
    def _to_event(row: dict) -> Event:
        venue = row.get("venue") or {}
        sources = row.get("sources") or []
        return Event(
            id=str(row["id"]),
            title=row["title"],
            category=Category(row["category"]),
            venue_name=venue.get("name") or "장소 정보 없음",
            district=venue.get("district"),
            start_date=row["start_date"],
            end_date=row["end_date"],
            price_type=PriceType(row.get("price_kind") or "unknown"),
            min_price=row.get("min_price"),
            max_price=row.get("max_price"),
            price_text=row.get("price_text"),
            description=row.get("description"),
            booking_url=row.get("booking_url"),
            registered_at=row["first_seen_at"],
            updated_at=row["updated_at"],
            sources=[
                SourceRef(
                    source=source["source"],
                    source_name=(
                        "KOPIS" if source["source"] == "kopis" else "문화포털"
                    ),
                    external_url=source.get("source_url"),
                    attribution=source["attribution"],
                )
                for source in sources
            ],
        )

    async def list_events(self) -> list[Event]:
        select = (
            "id,title,category,start_date,end_date,price_kind,min_price,max_price,"
            "price_text,description,booking_url,first_seen_at,updated_at,"
            "venue:venues(name,district),"
            "sources:event_sources(source,source_url,attribution)"
        )
        response = await self._request(
            "GET",
            "events",
            params={
                "select": select,
                "is_active": "eq.true",
                "end_date": f"gte.{date.today().isoformat()}",
                "limit": self.fetch_limit,
            },
        )
        return [self._to_event(row) for row in response.json()]

    async def get_event(self, event_id: str) -> Event | None:
        select = (
            "id,title,category,start_date,end_date,price_kind,min_price,max_price,"
            "price_text,description,booking_url,first_seen_at,updated_at,"
            "venue:venues(name,district),"
            "sources:event_sources(source,source_url,attribution)"
        )
        response = await self._request(
            "GET",
            "events",
            params={"select": select, "id": f"eq.{event_id}", "limit": 1},
        )
        rows = response.json()
        return self._to_event(rows[0]) if rows else None

    async def ingest_batch(self, records: list[dict]) -> dict[str, int]:
        if not records:
            return {"inserted_count": 0, "updated_count": 0}
        response = await self._request(
            "POST",
            "rpc/ingest_event_batch",
            json={"p_rows": records},
        )
        return response.json()

    async def create_sync_run(self, source: str) -> str:
        response = await self._request(
            "POST",
            "sync_runs",
            headers={"Prefer": "return=representation"},
            json={"source": source, "status": "running"},
        )
        return response.json()[0]["id"]

    async def finish_sync_run(
        self,
        run_id: str,
        *,
        status: str,
        fetched_count: int,
        inserted_count: int,
        updated_count: int,
        errors: list[str],
    ) -> None:
        await self._request(
            "PATCH",
            "sync_runs",
            params={"id": f"eq.{run_id}"},
            json={
                "status": status,
                "finished_at": datetime.now(UTC).isoformat(),
                "fetched_count": fetched_count,
                "inserted_count": inserted_count,
                "updated_count": updated_count,
                "error_count": len(errors),
                "errors": errors,
            },
        )

    async def aclose(self) -> None:
        await self.client.aclose()
