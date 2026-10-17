from datetime import UTC, date, datetime, timedelta

from app.models import Category, Event, PriceType, SourceRef


def fixture_events(today: date | None = None) -> list[Event]:
    base = today or date.today()
    now = datetime.now(UTC)
    return [
        Event(
            id="evt-sema-2026",
            title="도시의 온도: 서울을 다시 읽는 법",
            category=Category.EXHIBITION,
            venue_name="서울시립미술관 서소문본관",
            district="중구",
            start_date=base - timedelta(days=20),
            end_date=base + timedelta(days=9),
            price_type=PriceType.FREE,
            min_price=0,
            max_price=0,
            price_text="무료",
            description="fixture 데이터로 제공되는 전시 예시입니다.",
            booking_url="https://sema.seoul.go.kr/",
            registered_at=now - timedelta(days=25),
            updated_at=now - timedelta(hours=3),
            sources=[
                SourceRef(
                    source="culture_portal", source_name="문화포털", attribution="출처: 문화포털"
                )
            ],
        ),
        Event(
            id="evt-daehangno-play",
            title="어느 가을날의 편지",
            category=Category.PLAY,
            venue_name="대학로 예술극장",
            district="종로구",
            start_date=base - timedelta(days=5),
            end_date=base + timedelta(days=2),
            price_type=PriceType.PAID,
            min_price=30000,
            max_price=50000,
            price_text="R석 50,000원 / S석 30,000원",
            registered_at=now - timedelta(days=12),
            updated_at=now - timedelta(hours=2),
            sources=[
                SourceRef(
                    source="kopis",
                    source_name="KOPIS",
                    attribution="출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)",
                )
            ],
        ),
        Event(
            id="evt-blue-musical",
            title="뮤지컬 파랑새",
            category=Category.MUSICAL,
            venue_name="충무아트센터 중극장 블랙",
            district="중구",
            start_date=base + timedelta(days=3),
            end_date=base + timedelta(days=45),
            price_type=PriceType.PAID,
            min_price=44000,
            max_price=77000,
            price_text="44,000원~77,000원",
            registered_at=now - timedelta(days=4),
            updated_at=now - timedelta(hours=1),
            sources=[
                SourceRef(
                    source="kopis",
                    source_name="KOPIS",
                    attribution="출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)",
                )
            ],
        ),
        Event(
            id="evt-mmca-light",
            title="빛의 문법",
            category=Category.EXHIBITION,
            venue_name="국립현대미술관 서울",
            district="종로구",
            start_date=base + timedelta(days=10),
            end_date=base + timedelta(days=75),
            price_type=PriceType.PAID,
            min_price=5000,
            max_price=5000,
            price_text="5,000원",
            registered_at=now - timedelta(days=2),
            updated_at=now,
            sources=[
                SourceRef(
                    source="culture_portal", source_name="문화포털", attribution="출처: 문화포털"
                )
            ],
        ),
        Event(
            id="evt-free-play",
            title="한강 낭독극장",
            category=Category.PLAY,
            venue_name="노들섬 라이브하우스",
            district="용산구",
            start_date=base + timedelta(days=(5 - base.weekday()) % 7),
            end_date=base + timedelta(days=(6 - base.weekday()) % 7),
            price_type=PriceType.FREE,
            min_price=0,
            max_price=0,
            price_text="무료(사전예약)",
            registered_at=now - timedelta(days=1),
            updated_at=now,
            sources=[
                SourceRef(
                    source="culture_portal", source_name="문화포털", attribution="출처: 문화포털"
                )
            ],
        ),
        Event(
            id="evt-long-musical",
            title="뮤지컬 별의 노래",
            category=Category.MUSICAL,
            venue_name="샤롯데씨어터",
            district="송파구",
            start_date=base + timedelta(days=30),
            end_date=base + timedelta(days=89),
            price_type=PriceType.UNKNOWN,
            price_text="가격 미정",
            registered_at=now,
            updated_at=now,
            sources=[
                SourceRef(
                    source="kopis",
                    source_name="KOPIS",
                    attribution="출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)",
                )
            ],
        ),
    ]
