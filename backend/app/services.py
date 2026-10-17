from datetime import date, timedelta

from app.models import Category, Event, PriceType


def filter_events(
    events: list[Event],
    *,
    query: str | None = None,
    categories: set[Category] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    districts: set[str] | None = None,
    price_type: PriceType | None = None,
    quick: str | None = None,
) -> list[Event]:
    today = date.today()
    from_day = date_from or today
    to_day = date_to or today + timedelta(days=92)

    if quick == "today":
        from_day = to_day = today
    elif quick == "weekend":
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        from_day, to_day = saturday, saturday + timedelta(days=1)
    elif quick == "ending-soon":
        from_day, to_day = today, today + timedelta(days=7)

    normalized_query = (query or "").casefold().strip()
    result: list[Event] = []
    for event in events:
        if event.end_date < from_day or event.start_date > to_day:
            continue
        if categories and event.category not in categories:
            continue
        if districts and event.district not in districts:
            continue
        if price_type and event.price_type != price_type:
            continue
        if (
            normalized_query
            and normalized_query not in f"{event.title} {event.venue_name}".casefold()
        ):
            continue
        if quick == "ending-soon" and not (today <= event.end_date <= to_day):
            continue
        result.append(event)
    return result


def sort_events(events: list[Event], sort: str) -> list[Event]:
    if sort == "price":
        return sorted(
            events,
            key=lambda event: (event.min_price is None, event.min_price or 0, event.end_date),
        )
    if sort == "recent":
        return sorted(events, key=lambda event: event.registered_at, reverse=True)
    return sorted(events, key=lambda event: (event.end_date, event.start_date, event.title))
