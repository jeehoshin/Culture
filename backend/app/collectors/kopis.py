import asyncio
from datetime import date, timedelta
from xml.etree import ElementTree

import httpx

BASE_URL = "https://kopis.or.kr/openApi/restful"
MIN_INTERVAL_SECONDS = 0.25
MAX_TRIES = 4


def date_windows(start: date, end: date) -> list[tuple[date, date]]:
    """KOPIS의 31일 조회 제한에 맞춰 양 끝을 포함하는 구간으로 나눈다."""
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(end, cursor + timedelta(days=30))
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def parse_list_xml(payload: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(payload)
    return [
        {child.tag: (child.text or "").strip() for child in node} for node in root.findall(".//db")
    ]


class KopisClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self.client = client or httpx.AsyncClient(timeout=30)
        self._request_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def _paced_get(self, path: str, params: dict | None = None) -> httpx.Response:
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
                        f"{BASE_URL}/{path}", params={"service": self.api_key, **(params or {})}
                    )
            except httpx.HTTPError as exc:
                problem = exc
                continue
            if response.status_code >= 500 or (
                response.status_code == 400 and "Request Blocked" in response.text
            ):
                problem = httpx.HTTPStatusError(
                    "temporary KOPIS response", request=response.request, response=response
                )
                continue
            if response.status_code >= 400:
                raise RuntimeError(f"KOPIS request failed with HTTP {response.status_code}")
            return response
        raise RuntimeError("KOPIS request failed after retries") from problem

    async def list_performances(
        self, start: date, end: date, page: int = 1, genre_code: str | None = None
    ) -> list[dict[str, str]]:
        if (end - start).days > 30:
            raise ValueError("KOPIS list requests must cover at most 31 calendar days")
        params = {
            "stdate": start.strftime("%Y%m%d"),
            "eddate": end.strftime("%Y%m%d"),
            "cpage": page,
            "rows": 100,
            "signgucode": "11",
        }
        if genre_code:
            params["shcate"] = genre_code
        response = await self._paced_get(
            "pblprfr",
            params,
        )
        response.raise_for_status()
        return parse_list_xml(response.text)

    async def performance_detail(self, event_id: str) -> dict[str, str]:
        response = await self._paced_get(f"pblprfr/{event_id}")
        items = parse_list_xml(response.text)
        return items[0] if items else {}

    async def facility_detail(self, facility_id: str) -> dict[str, str]:
        response = await self._paced_get(f"prfplc/{facility_id}")
        items = parse_list_xml(response.text)
        return items[0] if items else {}
