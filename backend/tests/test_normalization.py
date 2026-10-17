from datetime import date

from app.models import PriceType
from app.normalization import DuplicateInput, duplicate_score, normalize_text, parse_price


def test_normalize_text_removes_punctuation_and_location_prefix() -> None:
    assert normalize_text("[서울] 뮤지컬: 파랑새") == "뮤지컬파랑새"


def test_parse_price() -> None:
    assert parse_price("무료") == (PriceType.FREE, 0, 0)
    assert parse_price("R석 77,000원 / S석 44,000원") == (PriceType.PAID, 44000, 77000)


def test_duplicate_score_accepts_minor_formatting_differences() -> None:
    left = DuplicateInput(
        "뮤지컬 파랑새", "충무아트센터 중극장 블랙", date(2026, 10, 20), date(2026, 12, 1)
    )
    right = DuplicateInput(
        "[서울] 뮤지컬: 파랑새", "충무아트센터 중극장블랙", date(2026, 10, 20), date(2026, 12, 1)
    )
    assert duplicate_score(left, right) >= 0.9
