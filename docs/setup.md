# 설정 및 배포 체크리스트

비밀키는 GitHub·Vercel·브라우저 코드에 넣지 않는다. 외부 API 키와 Supabase 서버 키는
Render 환경변수에만 저장한다.

## 1. 현재 준비된 API

- KOPIS: `KOPIS_API_KEY`
- 문화포털 전시정보(통합): `CULTURE_PORTAL_API_KEY`
- 문화포털 URL: `https://api.kcisa.kr/openapi/API_CCA_145/request`

공공데이터포털의 `한눈에보는문화정보조회서비스`는 2차 연동 대상으로 보류한다.

## 2. Supabase SQL 적용

1. Supabase Dashboard에서 프로젝트를 연다.
2. 왼쪽 메뉴에서 **SQL Editor**를 연다.
3. 처음 설정하는 프로젝트라면 `supabase/migrations/0001_initial.sql` 전체를 붙여 넣고 실행한다.
4. 이어서 `supabase/migrations/0002_ingest_rpc.sql` 전체를 붙여 넣고 실행한다.
5. **Table Editor**에서 `events`, `venues`, `raw_events`, `event_sources`, `sync_runs`가 보이는지 확인한다.

이미 `0001_initial.sql`을 실행했다면 3단계를 반복하지 않고 `0002_ingest_rpc.sql`만 실행한다.

## 3. Supabase 값 확인

Supabase Dashboard의 프로젝트 **Connect** 창 또는 **Settings → API Keys**에서 다음 값을 확인한다.

- Project URL → `SUPABASE_URL`
- 서버 전용 Secret key(`sb_secret_...`) → `SUPABASE_SECRET_KEY`

Secret key는 RLS를 우회할 수 있으므로 Render에만 넣고 Vercel의 `NEXT_PUBLIC_*` 변수에는
절대 넣지 않는다. 기존 프로젝트의 legacy service-role 키도 `SUPABASE_SERVICE_ROLE_KEY`로
호환되지만, 신규 설정은 Secret key를 사용한다.

## 4. Render 환경변수

Render Dashboard → 해당 Web Service → **Environment**에서 다음 값을 설정한다.

```text
APP_ENV=production
CORS_ORIGINS=https://culture-flame.vercel.app
USE_FIXTURE_DATA=false
KOPIS_API_KEY=<현재 발급 키>
CULTURE_PORTAL_API_KEY=<현재 발급 키>
CULTURE_PORTAL_API_URL=https://api.kcisa.kr/openapi/API_CCA_145/request
SUPABASE_URL=<Supabase Project URL>
SUPABASE_SECRET_KEY=<Supabase sb_secret_ 키>
SYNC_SECRET=<충분히 긴 임의 문자열>
SYNC_KOPIS_ENABLED=true
SYNC_CULTURE_PORTAL_ENABLED=true
CULTURE_PORTAL_MAX_PAGES=100
SUPABASE_FETCH_LIMIT=5000
```

`SYNC_SECRET`은 비밀번호 관리자에서 32자 이상 임의 문자열로 생성한다. 설정을 저장한 뒤
**Manual Deploy → Deploy latest commit**을 실행한다.

## 5. 배포 확인과 최초 동기화

먼저 다음 주소를 열어 `data_mode`가 `supabase`인지 확인한다.

```text
https://culture-qb0h.onrender.com/health
```

그다음 로컬 터미널에서 최초 동기화를 요청한다.

```bash
curl -X POST 'https://culture-qb0h.onrender.com/api/v1/sync' \
  -H 'X-Sync-Secret: Render에 설정한 SYNC_SECRET'
```

응답이 `{"status":"accepted"}`이면 수집이 백그라운드에서 시작된 것이다. 진행 상태는 다음에서
확인한다.

```text
https://culture-qb0h.onrender.com/api/v1/sync/status
```

`status`가 `succeeded` 또는 `partial`이 된 뒤 행사 목록 API와 Vercel 화면을 새로고침한다.

## 6. 로컬 동기화 방법

루트 `.env`에 Supabase 서버 값을 넣은 경우 다음 명령으로 동일한 작업을 로컬에서 실행할 수 있다.

```bash
cd backend
.venv/bin/python -m scripts.sync_now
```

## 7. Vercel

Vercel에는 공개 백엔드 주소만 필수다.

```text
NEXT_PUBLIC_API_URL=https://culture-qb0h.onrender.com
```

향후 Supabase 로그인을 연결할 때만 `NEXT_PUBLIC_SUPABASE_URL`과
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`를 추가한다. Secret/service-role 키는 절대 Vercel에 넣지 않는다.

## 8. 정기 동기화

최초 동기화와 데이터 품질 확인 후 Render Cron Job에서 `backend`를 Root Directory로 사용하고
다음 명령을 하루 1회 실행하도록 설정할 수 있다.

```text
python -m scripts.sync_now
```

Cron Job에도 Web Service와 동일한 API 및 Supabase 환경변수가 필요하다.
