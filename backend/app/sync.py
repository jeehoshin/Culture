import asyncio
import hashlib
import html
import json
import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse

from app.collectors.culture_portal import CulturePortalClient
from app.collectors.kopis import KopisClient, date_windows
from app.config import Settings
from app.models import Category
from app.normalization import normalize_text, parse_price
from app.repository import SupabaseRepository

SEOUL_DISTRICTS = (
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
)

SEOUL_VENUES: dict[str, str] = {
    "국립중앙박물관": "용산구",
    "국립현대미술관 서울": "종로구",
    "국립현대미술관서울": "종로구",
    "대한민국역사박물관": "종로구",
    "국립한글박물관": "용산구",
    "국립민속박물관": "종로구",
    "국립고궁박물관": "종로구",
    "국립중앙극장": "중구",
    "국립극단": "용산구",
    "예술의전당": "서초구",
    "한국영상자료원": "마포구",
    "국립어린이청소년도서관": "강남구",
    "서울관": "종로구",
}

SOURCE_META = {
    "kopis": {
        "api_documentation_url": "https://kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00077",
        "attribution": "출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)",
        "license_note": "KOPIS Open API 이용조건 및 출처표시 준수",
    },
    "culture_portal": {
        "api_documentation_url": "https://www.culture.go.kr/data/openapi/openapiView.do?id=598",
        "attribution": "출처: 한국문화정보원 문화공공데이터광장 전시정보(통합)",
        "license_note": "기관별 원문 저작권 및 문화공공데이터광장 이용조건 준수",
    },
}


def _clean_text(value: object, limit: int | None = None) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\[nr]|[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if limit else text


def _parse_date(value: object) -> date | None:
    text = _clean_text(value)
    match = re.search(r"(\d{4})[.\-/]?(\d{2})[.\-/]?(\d{2})", text)
    if not match:
        return None
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def _parse_period(value: object) -> tuple[date, date] | None:
    matches = re.findall(r"\d{4}[.\-/]?\d{2}[.\-/]?\d{2}", _clean_text(value))
    if not matches:
        return None
    start = _parse_date(matches[0])
    end = _parse_date(matches[1] if len(matches) > 1 else matches[0])
    if not start or not end or end < start:
        return None
    return start, end


def _http_url(value: object) -> str | None:
    text = _clean_text(value, 2000)
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _district(*values: object) -> str | None:
    text = " ".join(_clean_text(value) for value in values)
    for district in SEOUL_DISTRICTS:
        if district in text:
            return district
    for venue, district in SEOUL_VENUES.items():
        if venue in text:
            return district
    return None


def _is_seoul(*values: object) -> bool:
    text = " ".join(_clean_text(value) for value in values)
    return "서울" in text or _district(text) is not None


def _hash_payload(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _record(
    *,
    source: str,
    external_id: str,
    title: str,
    category: Category,
    venue_name: str,
    address: str | None,
    district: str | None,
    start_date: date,
    end_date: date,
    price_text: str | None,
    description: str | None,
    source_url: str | None,
    payload: dict,
) -> dict:
    price_kind, min_price, max_price = parse_price(price_text)
    meta = SOURCE_META[source]
    return {
        "source": source,
        "external_id": external_id,
        "payload": payload,
        "payload_hash": _hash_payload(payload),
        "title": title,
        "normalized_title": normalize_text(title),
        "category": category.value,
        "venue_name": venue_name or "장소 정보 없음",
        "normalized_venue_name": normalize_text(venue_name or "장소 정보 없음"),
        "address": address,
        "district": district,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "price_kind": price_kind.value,
        "min_price": min_price,
        "max_price": max_price,
        "price_text": price_text,
        "description": description,
        "booking_url": source_url,
        "source_url": source_url,
        "api_documentation_url": meta["api_documentation_url"],
        "attribution": meta["attribution"],
        "license_note": meta["license_note"],
    }


def normalize_culture_event(item: dict, today: date, horizon: date) -> dict | None:
    period = _parse_period(item.get("PERIOD"))
    if not period:
        return None
    start_date, end_date = period
    if end_date < today or start_date > horizon:
        return None
    title = _clean_text(item.get("TITLE"), 500)
    venue = _clean_text(item.get("EVENT_SITE"), 500)
    institution = _clean_text(item.get("CNTC_INSTT_NM"), 300)
    description = _clean_text(item.get("DESCRIPTION"), 5000)
    spatial = _clean_text(item.get("SPATIAL_COVERAGE"), 500)
    if not title or not _is_seoul(venue, institution, spatial, description):
        return None
    local_id = _clean_text(item.get("LOCAL_ID"), 300)
    if not local_id:
        return None
    external_id = f"{institution}:{local_id}" if institution else local_id
    url = _http_url(item.get("URL"))
    price = _clean_text(item.get("CHARGE"), 1000) or None
    return _record(
        source="culture_portal",
        external_id=external_id,
        title=title,
        category=Category.EXHIBITION,
        venue_name=venue or institution,
        address=spatial or None,
        district=_district(venue, institution, spatial, description),
        start_date=start_date,
        end_date=end_date,
        price_text=price,
        description=description or None,
        source_url=url,
        payload=item,
    )


def normalize_kopis_event(item: dict, detail: dict, facility: dict) -> dict | None:
    event_id = _clean_text(item.get("mt20id"))
    title = _clean_text(item.get("prfnm") or detail.get("prfnm"), 500)
    start_date = _parse_date(item.get("prfpdfrom") or detail.get("prfpdfrom"))
    end_date = _parse_date(item.get("prfpdto") or detail.get("prfpdto"))
    if not event_id or not title or not start_date or not end_date:
        return None
    genre = _clean_text(item.get("genrenm") or detail.get("genrenm"))
    category = Category.MUSICAL if "뮤지컬" in genre else Category.PLAY
    venue = _clean_text(item.get("fcltynm") or detail.get("fcltynm"), 500)
    address = _clean_text(facility.get("adres"), 1000) or None
    price = _clean_text(detail.get("pcseguidance"), 1000) or None
    source_url = f"https://kopis.or.kr/mob/db/pblprfrView.do?mt20Id={event_id}"
    description_parts = [detail.get("prfcast"), detail.get("prfcrew"), detail.get("dtguidance")]
    description = _clean_text(" · ".join(str(value or "") for value in description_parts), 5000)
    return _record(
        source="kopis",
        external_id=event_id,
        title=title,
        category=category,
        venue_name=venue,
        address=address,
        district=_district(address, venue),
        start_date=start_date,
        end_date=end_date,
        price_text=price,
        description=description or None,
        source_url=source_url,
        payload={"list": item, "detail": detail, "facility": facility},
    )


async def collect_culture(settings: Settings) -> tuple[list[dict], list[str]]:
    if not settings.culture_portal_api_key:
        return [], ["CULTURE_PORTAL_API_KEY is not configured"]
    client = CulturePortalClient(
        settings.culture_portal_api_key, settings.culture_portal_api_url
    )
    try:
        raw_items = await client.all_events(max_pages=settings.culture_portal_max_pages)
    finally:
        await client.aclose()
    today = date.today()
    horizon = today + timedelta(days=92)
    records = [normalize_culture_event(item, today, horizon) for item in raw_items]
    return [record for record in records if record], []


async def collect_kopis(settings: Settings) -> tuple[list[dict], list[str]]:
    if not settings.kopis_api_key:
        return [], ["KOPIS_API_KEY is not configured"]
    client = KopisClient(settings.kopis_api_key)
    start, end = date.today(), date.today() + timedelta(days=92)
    listed: dict[str, dict] = {}
    errors: list[str] = []
    try:
        for genre_code in ("AAAA", "GGGA"):
            for window_start, window_end in date_windows(start, end):
                page = 1
                while True:
                    items = await client.list_performances(
                        window_start, window_end, page=page, genre_code=genre_code
                    )
                    for item in items:
                        if item.get("mt20id"):
                            listed[item["mt20id"]] = item
                    if len(items) < 100:
                        break
                    page += 1

        detail_results = await asyncio.gather(
            *(client.performance_detail(event_id) for event_id in listed),
            return_exceptions=True,
        )
        details: dict[str, dict] = {}
        for event_id, result in zip(listed, detail_results, strict=True):
            if isinstance(result, Exception):
                errors.append(f"KOPIS detail failed: {event_id}")
            else:
                details[event_id] = result

        facility_ids = {
            detail.get("mt10id") for detail in details.values() if detail.get("mt10id")
        }
        facility_results = await asyncio.gather(
            *(client.facility_detail(facility_id) for facility_id in facility_ids),
            return_exceptions=True,
        )
        facilities: dict[str, dict] = {}
        for facility_id, result in zip(facility_ids, facility_results, strict=True):
            if isinstance(result, Exception):
                errors.append(f"KOPIS facility failed: {facility_id}")
            else:
                facilities[facility_id] = result
    finally:
        await client.client.aclose()

    records: list[dict] = []
    for event_id, item in listed.items():
        detail = details.get(event_id, {})
        facility = facilities.get(detail.get("mt10id"), {})
        record = normalize_kopis_event(item, detail, facility)
        if record:
            records.append(record)
    return records, errors


class SyncManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.state: dict = {"status": "idle", "started_at": None, "finished_at": None}

    async def run(self, settings: Settings) -> None:
        if self._lock.locked():
            return
        async with self._lock:
            self.state = {
                "status": "running",
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": None,
                "sources": {},
            }
            repository = SupabaseRepository(
                settings.supabase_url or "",
                settings.supabase_server_key or "",
                settings.supabase_fetch_limit,
            )
            try:
                collectors = []
                if settings.sync_kopis_enabled:
                    collectors.append(("kopis", collect_kopis))
                if settings.sync_culture_portal_enabled:
                    collectors.append(("culture_portal", collect_culture))
                for source, collector in collectors:
                    await self._sync_source(source, collector, settings, repository)
                try:
                    self.state["expired_deactivated"] = await repository.deactivate_expired_events()
                except RuntimeError as exc:
                    # Keep deployments compatible until the lifecycle migration is applied.
                    self.state["lifecycle_warning"] = str(exc)
                incomplete = any(
                    result["status"] != "succeeded"
                    for result in self.state["sources"].values()
                )
                self.state["status"] = "partial" if incomplete else "succeeded"
            except Exception as exc:  # noqa: BLE001 - background boundary records failures
                self.state["status"] = "failed"
                self.state["error"] = str(exc)
            finally:
                self.state["finished_at"] = datetime.now(UTC).isoformat()
                await repository.aclose()

    async def _sync_source(self, source, collector, settings, repository) -> None:
        run_id = await repository.create_sync_run(source)
        records: list[dict] = []
        errors: list[str] = []
        inserted = 0
        updated = 0
        status = "succeeded"
        try:
            records, errors = await collector(settings)
            for offset in range(0, len(records), 100):
                result = await repository.ingest_batch(records[offset : offset + 100])
                inserted += int(result.get("inserted_count") or 0)
                updated += int(result.get("updated_count") or 0)
            if errors:
                status = "partial" if records else "failed"
        except Exception as exc:  # noqa: BLE001 - one source must not prevent the other
            errors.append(str(exc))
            status = "failed"
        await repository.finish_sync_run(
            run_id,
            status=status,
            fetched_count=len(records),
            inserted_count=inserted,
            updated_count=updated,
            errors=errors[:100],
        )
        self.state["sources"][source] = {
            "status": status,
            "fetched_count": len(records),
            "inserted_count": inserted,
            "updated_count": updated,
            "error_count": len(errors),
            "errors": errors[:3],
        }


sync_manager = SyncManager()
