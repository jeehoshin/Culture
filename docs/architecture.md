# 아키텍처와 데이터 흐름

```text
문화포털 / KOPIS / (서울시)
          │ 서버 전용 키
          ▼
Render: FastAPI 수집기 ──▶ raw_events (원문 JSON/XML 변환본)
          │                    │
          │ 정규화/검증         │ 재처리 가능, 삭제 금지
          ▼                    │
venues ◀─ events ◀─ event_sources
          │
          ├── 공개 검색 API ──▶ Vercel: Next.js
          │
          └── favorites / attendance (Supabase JWT + RLS)
```

## 동기화

- 하루 2~4회 Render cron 또는 Supabase scheduled trigger가 `POST /api/v1/sync`를 호출한다.
- KOPIS는 31일 제한 때문에 3개월을 31일 이하 구간으로 나눠 호출한다.
- `source + external_id + payload_hash`가 같으면 원본을 중복 저장하지 않는다.
- 정규화는 멱등 upsert이며, 대표 행사는 원본 출처를 `event_sources`로 여러 개 연결한다.
- 삭제된 외부 데이터는 즉시 삭제하지 않고 `last_seen_at`으로 비활성 여부를 판단한다.

## 중복 판정

- 강한 일치: 정규화 제목, 시작일, 종료일, 정규화 장소가 모두 일치 → 자동 연결 후보(0.92 이상).
- 중간 일치: 제목 유사도와 날짜 일치, 장소 불일치/누락 → 수동 검토(0.72~0.92).
- 낮은 일치: 별도 행사로 유지.
- 원본 행은 어떤 병합 작업에서도 삭제하지 않는다.

## 보안 경계

- 외부 API 키와 Supabase Secret key는 Render에만 둔다.
- Next.js에는 `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, 공개 백엔드 URL만 둔다.
- Secret key는 수집 작업에만 사용한다. 사용자 요청은 Supabase JWT를 전달하고 RLS가 최종 권한을 검사한다.

