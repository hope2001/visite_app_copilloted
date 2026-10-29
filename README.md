# Visitor Management Platform

Enterprise visitor registration, check-in/check-out and audit trail.

- **Backend:** Python FastAPI, SQLAlchemy 2, Alembic, SQLite (`backend/`)
- **Frontend:** React 18, TypeScript, Vite, TanStack Query (`frontend/`)
- **Deployment:** Docker Compose. nginx serves the SPA and proxies `/api/` to the backend (same origin).

## Run with Docker

```powershell
Copy-Item .env.example .env   # then set a strong VMP_JWT_SECRET_KEY
docker compose up --build
```

Open http://localhost:8080. The database is stored in the `vmp-data` volume, and migrations run on startup.

### Demo users

If `VMP_SEED_PASSWORD` is set, demo data is seeded. All demo users share that password.

| Email                         | Role     |
| ----------------------------- | -------- |
| alice.employee@acme-corp.com  | Employee |
| bob.employee@acme-corp.com    | Employee |
| sam.security@acme-corp.com    | Security |
| ada.admin@acme-corp.com       | Admin    |

Leave `VMP_SEED_PASSWORD` empty in real deployments.

## Local development

### Backend (http://localhost:8000, API docs at `/docs`)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:VMP_JWT_SECRET_KEY = "dev-secret-at-least-32-characters-long"
$env:VMP_SEED_PASSWORD  = "DemoPassw0rd!2026"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload
```

### Frontend (http://localhost:5173, proxies `/api` to port 8000)

```powershell
cd frontend
npm install
npm run dev
```

## Quality checks

```powershell
# backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy app

# frontend
npm test
npm run typecheck
npm run lint
npm run build
```

## Visitor passes (QR)

Each registered visit has a unique QR visitor pass.

1. After registering a visit, the employee sees the pass on the visit page (only while the visit is
   _Expected_) and can print it or forward it to the visitor.
2. At the security desk, the officer scans the QR code with a handheld scanner, or pastes the code,
   in **Scan visitor pass**. The app shows the visit.
3. The officer checks the visitor's photo ID, then clicks **Check in**. The normal check-in rules
   and audit trail apply: the visit must be due today and still expected.

| Endpoint                            | Roles                              | Purpose                      |
| ----------------------------------- | ---------------------------------- | ---------------------------- |
| `GET /api/v1/visits/{id}/pass`      | Employee (registrant/host), Admin  | Get the pass code of a visit |
| `POST /api/v1/visits/pass-lookup`   | Security, Admin                    | Find the visit for a code    |

The code looks like `VP1-<52 Base32 characters>`. It encodes the visit id plus a 128-bit HMAC-SHA256
tag. The tag key is derived from `VMP_JWT_SECRET_KEY` and is separate from the JWT signing key.
Nothing is stored in the database.

Security notes:

- The QR code contains no personal data, and passes cannot be forged or guessed without the
  server secret.
- Scanning only identifies the visit and changes nothing. Check-in is still an explicit,
  role-checked action, and a pass cannot be used to check in twice.
- Cancelling a visit makes its pass useless, because cancelled visits cannot be checked in.
- Invalid, forged and unknown passes all get the same `404 VISITOR_PASS_INVALID` response.
- The code is sent in the request body, not the URL, and is never logged. Each successful lookup
  is logged with the visit id and the officer's user id.
- **Rotating `VMP_JWT_SECRET_KEY` invalidates all outstanding passes** (and sessions). Reprint the
  passes for upcoming visits after a rotation.

## Configuration

All backend settings use the `VMP_` prefix. See `backend/app/core/config.py`.

| Variable                          | Purpose                                            |
| --------------------------------- | -------------------------------------------------- |
| `VMP_JWT_SECRET_KEY`              | Required. Must be at least 32 characters.          |
| `VMP_DATABASE_URL`                | SQLAlchemy URL (default: SQLite file)              |
| `VMP_SITE_TIMEZONE`               | IANA timezone used to compute "today's" visits     |
| `VMP_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime                                       |
| `VMP_SEED_PASSWORD`               | Seeds demo users and visits when set               |
