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
5. 이어서 `supabase/migrations/0003_auth_links_and_lifecycle.sql` 전체를 붙여 넣고 실행한다.
6. **Table Editor**에서 `events`, `venues`, `raw_events`, `event_sources`, `sync_runs`가 보이는지 확인한다.

이미 `0001_initial.sql`과 `0002_ingest_rpc.sql`을 실행했다면 앞의 두 파일은 반복하지 않고
`0003_auth_links_and_lifecycle.sql`만 실행한다. 이 파일은 기존 KOPIS 링크를 정상 주소로 바꾸고,
종료 행사를 비활성화하는 함수를 추가한다.

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

그다음 로컬 터미널에서 최초 동기화를 요청한다. 아래 첫 명령을 실행하면 비밀값 입력을 기다린다.
Render의 `SYNC_SECRET` 값을 붙여 넣고 Enter를 누른다. 입력 중에는 화면에 글자가 표시되지 않는 것이 정상이다.

```bash
read -s "CULTURE_SYNC_SECRET?Render SYNC_SECRET: "
curl --fail-with-body -X POST "https://culture-qb0h.onrender.com/api/v1/sync" -H "X-Sync-Secret: ${CULTURE_SYNC_SECRET}"
unset CULTURE_SYNC_SECRET
```

URL 앞뒤에 `[ ]` 또는 `( )`를 붙이지 않는다. 문서의 설명용 문자열을 그대로 쓰는 것이 아니라
실제로 Render에 저장한 `SYNC_SECRET` 값을 입력해야 한다.

응답이 `{"status":"accepted"}`이면 수집이 백그라운드에서 시작된 것이다. 진행 상태는 다음에서
확인한다.

```text
https://culture-qb0h.onrender.com/api/v1/sync/status
```

`status`가 `succeeded` 또는 `partial`이 된 뒤 행사 목록 API와 Vercel 화면을 새로고침한다.

특정 소스만 다시 동기화할 때는 URL에 `source`를 지정할 수 있다.

```text
?source=kopis
?source=culture_portal
```

## 6. 로컬 동기화 방법

루트 `.env`에 Supabase 서버 값을 넣은 경우 다음 명령으로 동일한 작업을 로컬에서 실행할 수 있다.

```bash
cd backend
.venv/bin/python -m scripts.sync_now
```

## 7. Vercel과 로그인

Vercel Dashboard → 프로젝트 → **Settings → Environment Variables**에 다음 공개값을 추가한다.

```text
NEXT_PUBLIC_API_URL=https://culture-qb0h.onrender.com
NEXT_PUBLIC_SUPABASE_URL=<Supabase Project URL>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<Supabase Publishable key>
```

Supabase Dashboard → **Authentication → URL Configuration**에서 다음을 설정한다.

```text
Site URL: https://culture-flame.vercel.app
Redirect URLs:
https://culture-flame.vercel.app/**
http://localhost:3000/**
```

환경변수 저장 후 Vercel의 **Deployments**에서 최신 배포를 Redeploy한다. 화면 상단의 로그인 버튼에서
이메일을 입력하면 매직링크가 발송된다. 로그인 전에 같은 브라우저에 저장한 관심·관람 기록은 첫 로그인 때
계정 데이터로 이전된다. Publishable key는 브라우저 공개용이며, Secret/service-role 키는 절대 Vercel에 넣지 않는다.

## 8. 정기 동기화

최초 동기화와 데이터 품질 확인 후 Render Cron Job에서 `backend`를 Root Directory로 사용하고
다음 명령을 하루 1회 실행하도록 설정할 수 있다.

```text
python -m scripts.sync_now
```

Cron Job에도 Web Service와 동일한 API 및 Supabase 환경변수가 필요하다.

정기 동기화 때 종료일이 지난 `events`는 `is_active=false`로 자동 전환된다. 화면 API도 항상
`end_date >= 오늘` 조건을 적용하므로 정기 작업 사이에도 종료 행사가 노출되지 않는다. 사용자 관람 기록,
출처 연결, 원본 payload 보존을 위해 행을 물리 삭제하지 않는다.
