# Seoul Culture Finder

서울에서 현재 진행 중이거나 3개월 안에 열리는 전시·연극·뮤지컬을 한곳에서 검색하는 MVP입니다.

## 구성

- `frontend/`: Next.js 16 + TypeScript
- `backend/`: FastAPI, 외부 API 수집·정규화·검색 API
- `supabase/`: PostgreSQL 스키마, RLS 정책, 인덱스
- `docs/`: 요구사항, 데이터 흐름, API 조사와 실험 기록

## 빠른 시작

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload --port 8000

# 새 터미널
cd frontend
npm install
npm run dev
```

API 키가 없어도 6개의 fixture 행사로 검색 UI를 확인할 수 있습니다. 실데이터 모드는
KOPIS·문화포털을 수집해 Supabase에 저장한 뒤 목록 API가 해당 데이터를 읽습니다.

```bash
cd backend
.venv/bin/python -m scripts.run_experiment --source fixtures
.venv/bin/python -m scripts.run_experiment --source kopis
.venv/bin/python -m scripts.sync_now
.venv/bin/pytest
```

실제 API 실험은 `.env`에 키를 넣은 후 실행합니다.

```bash
cd backend
.venv/bin/python -m scripts.run_experiment --source live
```

자세한 설정은 [docs/setup.md](docs/setup.md)를 참고하세요.

