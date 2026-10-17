import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

from app.models import PriceType


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    text = re.sub(r"\[[^]]+\]|\([^)]*공연\)", " ", text)
    return re.sub(r"[^0-9a-z가-힣]+", "", text)


def parse_price(value: str | None) -> tuple[PriceType, int | None, int | None]:
    text = (value or "").strip()
    if not text:
        return PriceType.UNKNOWN, None, None
    if re.search(r"무료|free", text, re.IGNORECASE) and not re.search(r"유료", text):
        return PriceType.FREE, 0, 0
    numbers = [int(number.replace(",", "")) for number in re.findall(r"\d[\d,]*", text)]
    plausible = [number for number in numbers if number >= 1000]
    if plausible:
        return PriceType.PAID, min(plausible), max(plausible)
    if re.search(r"원|유료", text):
        return PriceType.PAID, None, None
    return PriceType.UNKNOWN, None, None


@dataclass(slots=True)
class DuplicateInput:
    title: str
    venue: str
    start_date: date
    end_date: date


def duplicate_score(left: DuplicateInput, right: DuplicateInput) -> float:
    title_score = SequenceMatcher(
        None, normalize_text(left.title), normalize_text(right.title)
    ).ratio()
    venue_score = SequenceMatcher(
        None, normalize_text(left.venue), normalize_text(right.venue)
    ).ratio()
    start_score = 1.0 if left.start_date == right.start_date else 0.0
    end_score = 1.0 if left.end_date == right.end_date else 0.0
    return round(title_score * 0.45 + venue_score * 0.2 + start_score * 0.2 + end_score * 0.15, 4)
