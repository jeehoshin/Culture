import asyncio
from dataclasses import dataclass

import httpx

MIN_INTERVAL_SECONDS = 0.4
MAX_TRIES = 4


@dataclass(slots=True)
class CulturePortalPage:
    items: list[dict]
    total_count: int
    page: int
    rows: int


class CulturePortalAPIError(RuntimeError):
    def __init__(self, result_code: str, message: str):
        super().__init__(f"Culture Portal API error {result_code}: {message}")
        self.result_code = result_code


def parse_json_payload(payload: dict, page: int, rows: int) -> CulturePortalPage:
    response = payload.get("response") or {}
    header = response.get("header") or {}
    result_code = str(header.get("resultCode") or "")
    if result_code != "0000":
        message = header.get("resultMsg") or "unknown culture portal error"
        raise CulturePortalAPIError(result_code, message)
    body = response.get("body") or {}
    items_node = (body.get("items") or {}).get("item") or []
    if isinstance(items_node, dict):
        items_node = [items_node]
    return CulturePortalPage(
        items=[item for item in items_node if isinstance(item, dict)],
        total_count=int(body.get("totalCount") or 0),
        page=int(body.get("pageNo") or page),
        rows=int(body.get("numOfRows") or rows),
    )


class CulturePortalClient:
    def __init__(self, api_key: str, api_url: str, client: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self.api_url = api_url
        self.client = client or httpx.AsyncClient(timeout=60)
        self._request_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def _get(self, params: dict) -> httpx.Response:
        problem: Exception | None = None
        for attempt in range(MAX_TRIES):
            if attempt:
                await asyncio.sleep(1.5 * attempt)
            try:
                async with self._request_lock:
                    loop = asyncio.get_running_loop()
                    delay = self._next_request_at - loop.time()
                    if delay > 0:
                        await asyncio.sleep(delay)
                    self._next_request_at = loop.time() + MIN_INTERVAL_SECONDS
                    response = await self.client.get(
                        self.api_url,
                        params={"serviceKey": self.api_key, **params},
                        headers={"Accept": "application/json"},
                    )
            except httpx.HTTPError as exc:
                problem = exc
                continue
            if response.status_code in {408, 429} or response.status_code >= 500:
                problem = RuntimeError(
                    f"Culture Portal temporary HTTP error {response.status_code}"
                )
                continue
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Culture Portal request failed with HTTP {response.status_code}"
                )
            return response
        detail = str(problem) if problem else "unknown network error"
        raise RuntimeError(f"Culture Portal request failed after retries: {detail}") from problem

    async def list_events(self, page: int = 1, rows: int = 100) -> CulturePortalPage:
        for attempt in range(MAX_TRIES):
            response = await self._get({"numOfRows": rows, "pageNo": page})
            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError("Culture Portal returned a non-JSON response") from exc
            try:
                return parse_json_payload(payload, page, rows)
            except CulturePortalAPIError as exc:
                if exc.result_code not in {"22", "23", "0022", "0023", "99", "0099"}:
                    raise
                if attempt == MAX_TRIES - 1:
                    raise
                await asyncio.sleep(2 * (attempt + 1))
        raise RuntimeError("Culture Portal request failed after retries")

    async def all_events(self, rows: int = 100, max_pages: int = 100) -> list[dict]:
        first = await self.list_events(page=1, rows=rows)
        items = list(first.items)
        total_pages = min(max_pages, max(1, (first.total_count + rows - 1) // rows))
        for page in range(2, total_pages + 1):
            current = await self.list_events(page=page, rows=rows)
            if not current.items:
                break
            items.extend(current.items)
        return items

    async def aclose(self) -> None:
        await self.client.aclose()
