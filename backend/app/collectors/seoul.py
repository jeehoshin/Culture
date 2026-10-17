from urllib.parse import quote

import httpx


class SeoulCultureAPIError(RuntimeError):
    pass


class SeoulCultureClient:
    def __init__(
        self,
        api_key: str | None,
        api_url: str = "http://openapi.seoul.go.kr:8088",
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key or "sample"
        self.api_url = api_url.rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=60)

    async def list_exhibitions(self) -> list[dict]:
        page_size = 5 if self.api_key == "sample" else 1000
        rows: list[dict] = []
        start = 1
        while True:
            end = start + page_size - 1
            url = (
                f"{self.api_url}/{self.api_key}/json/culturalEventInfo/"
                f"{start}/{end}/{quote('전시')}"
            )
            response = await self.client.get(url)
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise SeoulCultureAPIError("서울시 API가 JSON이 아닌 응답을 반환했습니다.") from exc
            node = payload.get("culturalEventInfo")
            if not node:
                result = payload.get("RESULT") or {}
                raise SeoulCultureAPIError(
                    f"서울시 API 오류 {result.get('CODE', 'unknown')}: "
                    f"{result.get('MESSAGE', 'unknown error')}"
                )
            result = node.get("RESULT") or {}
            if result.get("CODE") != "INFO-000":
                raise SeoulCultureAPIError(
                    f"서울시 API 오류 {result.get('CODE')}: {result.get('MESSAGE')}"
                )
            current = [row for row in (node.get("row") or []) if isinstance(row, dict)]
            rows.extend(current)
            total = int(node.get("list_total_count") or 0)
            if self.api_key == "sample" or end >= total or not current:
                break
            start = end + 1
        return rows

    async def aclose(self) -> None:
        await self.client.aclose()
