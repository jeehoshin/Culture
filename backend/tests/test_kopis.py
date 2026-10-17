from datetime import date, timedelta
from itertools import pairwise

from app.collectors.kopis import date_windows


def test_date_windows_respects_31_day_limit() -> None:
    windows = date_windows(date(2026, 10, 17), date(2027, 1, 17))
    assert windows[0] == (date(2026, 10, 17), date(2026, 11, 16))
    assert windows[-1][1] == date(2027, 1, 17)
    assert all((end - start).days <= 30 for start, end in windows)
    assert all(left[1] + timedelta(days=1) == right[0] for left, right in pairwise(windows))
