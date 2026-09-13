# NWay — intercity bus booking / междугородние автобусы

Foundation of a seat-booking platform: origin → destination → date → trip → seat → phone → payment → ticket.

Пассажирский интерфейс на русском. API и код — на английском.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async), PostgreSQL, Alembic, Pydantic v2, JWT
- Frontend: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS
- Infra: Docker Compose (postgres, backend, frontend)

## Money

Amounts are **integer minor units** (1/100 of the currency). Never floats.

`1500000` = `15000.00` UZS (tiyin-equivalent). Always stored with `currency` (`UZS` / `KZT` / `RUB` / `USD`). Default currency: `DEFAULT_CURRENCY` env.

All timestamps are UTC. City timezone is for display only.

Public booking codes look like `JZK-8F2KQ`. Database UUIDs are never shown to passengers.

## Deploy on Railway

Railway fails on the repo root with Railpack because this is a monorepo. Use **Docker** and these services:

### 1. PostgreSQL
Add the **PostgreSQL** plugin. Copy `DATABASE_URL` into the backend service variables.

### 2. Backend (API)
- **Root Directory:** leave empty (repo root) — uses root `Dockerfile` + `railway.toml`
- **Variables:**
  - `DATABASE_URL` — from Postgres plugin (auto-converted to asyncpg)
  - `JWT_SECRET` — long random string
  - `CORS_ORIGINS` — your frontend public URL (comma-separated)
  - `DEBUG=false`
  - `RUN_SEED=true` — first deploy only; set `false` later if you want

### 3. Frontend (optional second service)
- **Root Directory:** `/frontend`
- **Variables:**
  - `BACKEND_URL` — public backend URL, e.g. `https://your-api.up.railway.app`
  - Or set build arg `VITE_API_BASE_URL` to the same URL (direct browser → API calls)

Redeploy after pushing. If build still uses Railpack, set **Settings → Build → Builder** to **Dockerfile**.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000  
- Swagger: http://localhost:8000/docs  
- Frontend: http://localhost:8080  

Backend waits for Postgres, runs migrations, then seeds demo data.

## Local run (without Docker for apps)

Compose files are ready (`docker compose up --build`). If Docker is not installed, local PostgreSQL works with user/password `nway`/`nway` on `localhost:5432`.

Start Postgres (Compose is enough for DB only):

```bash
docker compose up postgres -d
```

Backend (reads env from project root `.env`):

```bash
cp .env.example .env
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`.

## Seed / expire jobs

```bash
cd backend
python -m app.cli seed
python -m app.cli expire-reservations
```

`expire-reservations` frees seats when the 10-minute hold ends **or** when unpaid bookings pass `OFFLINE_BOOKING_DEADLINE_MINUTES` before departure (default 120).

## Tests

Needs PostgreSQL. Default test DB is `nway_test` (created from `DATABASE_URL`).

```bash
cd backend
pytest
```

Frontend smoke:

```bash
cd frontend
npm run build
```

## Demo credentials

| Role | Login | Password |
|------|--------|----------|
| Company admin | `admin@demo.local` | `SEED_ADMIN_PASSWORD` (default `changeme`) |
| Superadmin | `superadmin@demo.local` | `SEED_SUPERADMIN_PASSWORD` (default `changeme`) |
| Passenger phone | `+998901234567` | OTP in DEBUG response / server logs |

Admin UI: http://localhost:8080/login (or Vite http://localhost:5173/login)

## API

Versioned REST: `/api/v1/`

- Public: cities, trip search, seats, reservations, payments, lookup, tickets, OTP, admin login
- Admin: dashboard, cities, routes, buses, layouts, trips, reservations (state-machine actions), payments, passengers, users, companies

Errors:

```json
{ "error": { "code": "SEAT_ALREADY_RESERVED", "message": "..." } }
```

## Architecture notes

- Modular monolith. Business logic in services, thin handlers.
- Seat availability is **per trip**. `ReservationSeat.is_active_hold` + partial unique index `(trip_id, seat_id) WHERE is_active_hold`.
- Booking hold: `BOOKING_HOLD_MINUTES` (10). Large bookings (`LARGE_BOOKING_THRESHOLD`, default 4) go to `awaiting_admin_approval`.
- Payments are entities. MVP provider: `MockPaymentProvider`.
- Auth: Phone OTP + admin password. JWT access + refresh.
- Redis-ready rate-limit interface exists; MVP is a no-op (not fake security).
