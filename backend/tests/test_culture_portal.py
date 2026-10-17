from datetime import date

import httpx
import pytest

from app.collectors.culture_portal import CulturePortalClient, parse_json_payload
from app.sync import normalize_culture_event


def test_parse_culture_portal_response() -> None:
    page = parse_json_payload(
        {
            "response": {
                "header": {"resultCode": "0000", "resultMsg": "OK"},
                "body": {
                    "items": {"item": [{"TITLE": "서울의 빛"}]},
                    "totalCount": "12",
                    "pageNo": "1",
                    "numOfRows": "10",
                },
            }
        },
        page=1,
        rows=10,
    )
    assert page.total_count == 12
    assert page.items == [{"TITLE": "서울의 빛"}]


def test_parse_culture_portal_error() -> None:
    with pytest.raises(RuntimeError, match="not registered"):
        parse_json_payload(
            {
                "response": {
                    "header": {"resultCode": "0030", "resultMsg": "not registered"}
                }
            },
            page=1,
            rows=10,
        )


def test_normalize_current_seoul_exhibition() -> None:
    record = normalize_culture_event(
        {
            "TITLE": "서울 전시",
            "CNTC_INSTT_NM": "국립중앙박물관",
            "LOCAL_ID": "EX-1",
            "EVENT_SITE": "국립중앙박물관 특별전시실",
            "PERIOD": "2026-10-01~2026-12-31",
            "CHARGE": "성인 5,000원",
            "URL": "https://example.com/exhibition",
        },
        today=date(2026, 10, 17),
        horizon=date(2027, 1, 17),
    )
    assert record is not None
    assert record["category"] == "exhibition"
    assert record["district"] == "용산구"
    assert record["min_price"] == 5000


def test_normalize_rejects_non_seoul_exhibition() -> None:
    record = normalize_culture_event(
        {
            "TITLE": "강원의 고대",
            "CNTC_INSTT_NM": "국립춘천박물관",
            "LOCAL_ID": "EX-2",
            "EVENT_SITE": "국립춘천박물관",
            "PERIOD": "2026-10-01~2026-12-31",
        },
        today=date(2026, 10, 17),
        horizon=date(2027, 1, 17),
    )
    assert record is None


@pytest.mark.asyncio
async def test_culture_portal_retry_error_keeps_http_status(monkeypatch) -> None:
    client = CulturePortalClient("test-key", "https://example.com")

    async def fail(*_args, **_kwargs):
        return httpx.Response(503)

    monkeypatch.setattr(client.client, "get", fail)
    monkeypatch.setattr("app.collectors.culture_portal.asyncio.sleep", lambda *_args: _no_wait())
    with pytest.raises(RuntimeError, match="temporary HTTP error 503"):
        await client.list_events(rows=1)
    await client.aclose()


async def _no_wait() -> None:
    return None
