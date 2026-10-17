from datetime import date

import httpx
import pytest

from app.collectors.seoul import SeoulCultureClient
from app.sync import normalize_seoul_event


@pytest.mark.asyncio
async def test_seoul_client_uses_exhibition_filter_with_sample_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "/sample/json/culturalEventInfo/1/5/" in str(request.url)
        return httpx.Response(
            200,
            json={
                "culturalEventInfo": {
                    "list_total_count": 3324,
                    "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
                    "row": [{"CODENAME": "전시/미술", "TITLE": "서울의 빛"}],
                }
            },
        )

    client = SeoulCultureClient(
        None, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        rows = await client.list_exhibitions()
    finally:
        await client.aclose()
    assert rows[0]["TITLE"] == "서울의 빛"


def test_normalize_seoul_exhibition() -> None:
    record = normalize_seoul_event(
        {
            "CODENAME": "전시/미술",
            "GUNAME": "종로구",
            "TITLE": "다시 쓰기: 몸으로서의 도시",
            "PLACE": "예술가의 집",
            "USE_FEE": "무료",
            "STRTDATE": "2026-11-02 00:00:00.0",
            "END_DATE": "2026-11-08 00:00:00.0",
            "HMPG_ADDR": "https://culture.seoul.go.kr/event?cultcode=159800",
        },
        today=date(2026, 10, 17),
        horizon=date(2027, 1, 17),
    )
    assert record is not None
    assert record["source"] == "seoul"
    assert record["category"] == "exhibition"
    assert record["external_id"] == "159800"
    assert record["district"] == "종로구"
