# 설정 및 배포 체크리스트

## 1. 키 발급

1. KOPIS PC 웹에서 Open API 인증키를 신청한다.
2. 문화공공데이터광장에서 공연정보(통합), 전시정보(통합) API 활용신청 후 endpoint와 키를 확인한다.
3. `.env` 또는 Render Secret에만 `KOPIS_API_KEY`, `CULTURE_PORTAL_API_KEY`, `CULTURE_PORTAL_API_URL`을 넣는다.

## 2. Supabase

1. 새 Supabase 프로젝트를 만든다.
2. SQL Editor에서 `supabase/migrations/0001_initial.sql`을 실행한다.
3. Render에는 URL과 service-role 키, Vercel에는 URL과 anon 키만 등록한다.
4. Email 또는 OAuth 인증 공급자를 활성화한다.

## 3. Render

- Root directory: `backend`
- Build: `pip install -e .`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- 환경변수: 루트 `.env.example` 항목과 `USE_FIXTURE_DATA=false`

## 4. Vercel

- Root directory: `frontend`
- `NEXT_PUBLIC_API_URL=https://<render-service>`
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 5. 운영 전 확인

- fixture가 아닌 실제 3개월 데이터를 대상으로 `run_experiment --source live` 실행
- 누락률·가격 파싱률·중복 후보를 검토한 뒤 스키마 필드 확정
- KOPIS 출처 문구, 원문 링크, 최종 갱신 시각 표시 확인
- 문화포털 이미지/텍스트 재사용 범위 확인

