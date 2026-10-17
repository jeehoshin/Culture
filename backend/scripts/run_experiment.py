import argparse
import asyncio
import json
from collections import Counter
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path

from app.collectors.culture_portal import CulturePortalClient
from app.collectors.kopis import KopisClient, date_windows
from app.config import get_settings
from app.fixtures import fixture_events
from app.normalization import DuplicateInput, duplicate_score, parse_price


def analyze(items: list[dict]) -> dict:
    fields = ["title", "venue", "start_date", "end_date", "price"]
    fields.extend(
        field for field in ("address", "genre", "state") if any(field in item for item in items)
    )
    completeness = {
        field: round(sum(bool(item.get(field)) for item in items) / max(len(items), 1), 3)
        for field in fields
    }
    duplicate_candidates = []
    for left, right in combinations(items, 2):
        score = duplicate_score(
            DuplicateInput(left["title"], left["venue"], left["start_date"], left["end_date"]),
            DuplicateInput(right["title"], right["venue"], right["start_date"], right["end_date"]),
        )
        if score >= 0.72:
            duplicate_candidates.append({"left": left["id"], "right": right["id"], "score": score})
    report = {
        "count": len(items),
        "completeness": completeness,
        "duplicate_candidates": duplicate_candidates,
    }
    if any("genre" in item for item in items):
        report["genre_counts"] = dict(Counter(item.get("genre") or "unknown" for item in items))
        report["state_counts"] = dict(Counter(item.get("state") or "unknown" for item in items))
        report["parsed_price_counts"] = dict(
            Counter(parse_price(item.get("price"))[0].value for item in items)
        )
    return report


def fixture_rows() -> list[dict]:
    events = fixture_events()
    rows = [
        {
            "id": item.id,
            "title": item.title,
            "venue": item.venue_name,
            "start_date": item.start_date,
            "end_date": item.end_date,
            "price": item.price_text,
        }
        for item in events
    ]
    duplicate = dict(rows[2])
    duplicate.update(
        id="culture-duplicate", title="[서울] 뮤지컬 파랑새", venue="충무아트센터 중극장블랙"
    )
    rows.append(duplicate)
    return rows


async def live_rows() -> list[dict]:
    settings = get_settings()
    if not settings.kopis_api_key or not settings.culture_portal_api_key:
        raise SystemExit("live mode requires KOPIS_API_KEY and CULTURE_PORTAL_API_KEY")
    start, end = date.today(), date.today() + timedelta(days=30)
    kopis, culture = await asyncio.gather(
        KopisClient(settings.kopis_api_key).list_performances(start, end),
        CulturePortalClient(
            settings.culture_portal_api_key, settings.culture_portal_api_url
        ).list_events(),
    )
    rows: list[dict] = []
    for item in kopis:
        rows.append(
            {
                "id": f"kopis:{item.get('mt20id')}",
                "title": item.get("prfnm", ""),
                "venue": item.get("fcltynm", ""),
                "start_date": date.fromisoformat(item["prfpdfrom"].replace(".", "-")),
                "end_date": date.fromisoformat(item["prfpdto"].replace(".", "-")),
                "price": "",
            }
        )
    for index, item in enumerate(culture):
        period = str(item.get("PERIOD") or item.get("period") or "").replace(".", "-").split("~")
        if len(period) != 2:
            continue
        try:
            start_date, end_date = (date.fromisoformat(value.strip()) for value in period)
        except ValueError:
            continue
        rows.append(
            {
                "id": f"culture:{item.get('id', index)}",
                "title": item.get("TITLE") or item.get("title") or "",
                "venue": item.get("EVENT_SITE") or item.get("eventSite") or "",
                "start_date": start_date,
                "end_date": end_date,
                "price": item.get("CHARGE") or item.get("charge") or "",
            }
        )
    return rows


async def kopis_rows() -> list[dict]:
    settings = get_settings()
    if not settings.kopis_api_key:
        raise SystemExit("kopis mode requires KOPIS_API_KEY")

    start, end = date.today(), date.today() + timedelta(days=92)
    client = KopisClient(settings.kopis_api_key)
    picked_by_genre: dict[str, dict[str, dict]] = {"AAAA": {}, "GGGA": {}}
    try:
        for genre_code in ("AAAA", "GGGA"):
            for window_start, window_end in date_windows(start, end):
                for item in await client.list_performances(
                    window_start, window_end, genre_code=genre_code
                ):
                    if item.get("mt20id"):
                        picked_by_genre[genre_code][item["mt20id"]] = item

        rows: list[dict] = []
        selected = [
            pair
            for genre_code in ("AAAA", "GGGA")
            for pair in list(picked_by_genre[genre_code].items())[:20]
        ]
        for event_id, item in selected:
            detail = await client.performance_detail(event_id)
            facility = {}
            if detail.get("mt10id"):
                facility = await client.facility_detail(detail["mt10id"])
            rows.append(
                {
                    "id": f"kopis:{event_id}",
                    "title": item.get("prfnm", ""),
                    "venue": item.get("fcltynm", ""),
                    "start_date": date.fromisoformat(item["prfpdfrom"].replace(".", "-")),
                    "end_date": date.fromisoformat(item["prfpdto"].replace(".", "-")),
                    "price": detail.get("pcseguidance", ""),
                    "address": facility.get("adres", ""),
                    "genre": item.get("genrenm", ""),
                    "state": item.get("prfstate", ""),
                }
            )
        return rows
    finally:
        await client.client.aclose()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["fixtures", "kopis", "live"], default="fixtures")
    args = parser.parse_args()
    if args.source == "fixtures":
        rows = fixture_rows()
    elif args.source == "kopis":
        rows = await kopis_rows()
    else:
        rows = await live_rows()
    report = analyze(rows)
    output = Path("experiment-output")
    output.mkdir(exist_ok=True)
    path = output / f"{args.source}-report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"saved: {path}")


if __name__ == "__main__":
    asyncio.run(main())
