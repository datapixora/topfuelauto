# TopFuel Auto Monorepo

Search-first marketplace MVP across web, API, and mobile.

## Stack
- Backend: FastAPI + SQLAlchemy + Postgres + Redis + Celery
- Web: Next.js 14 (App Router) + Tailwind
- Mobile: Flutter + Riverpod + Dio
- Search: PostgreSQL full-text + pg_trgm + unaccent

## Local Run
1) `cp .env.example .env`
2) `docker compose up --build`
3) In another shell: `docker compose exec api alembic upgrade head`
4) Seed listings: `docker compose exec api python scripts/seed_listings.py`
5) Visit web at http://localhost:3000 and search “Nissan GT-R 2005” (API at http://localhost:8000)

## API Notes
- Health: `GET /health`
- Auth: `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- Listings: `GET /api/v1/listings`, `GET /api/v1/listings/{id}`
- Search: `GET /api/v1/search?q=...&year_min=&year_max=&price_min=&price_max=&location=`
- VIN: `GET /api/v1/vin/decode?vin=...` (all users), `GET /api/v1/vin/history?vin=...` (Pro only, returns placeholder)
- Broker: `POST /api/v1/broker/request-bid` (auth), `GET /api/v1/broker/leads/me`

## Search Implementation
- `search_text` and `search_tsv` columns
- Postgres extensions: `unaccent`, `pg_trgm`
- Ranking combines `ts_rank` + trigram similarity + optional budget proximity

## Seed Data
- `api/scripts/seed_listings.py` inserts ~50 listings
- Includes Nissan GT-R 2005 variants and Skyline/GTR synonyms

## Hosting Plan
- Production API + worker + Postgres + Redis: Render
- Web (Next.js): Vercel
- DNS/SSL + redirects: Cloudflare
  - Primary domain: `topfuelauto.com`
  - Secondary (typo): `tupfuelauto.com` -> 301 redirect to primary via Cloudflare Rules
  - Subdomains: `www.topfuelauto.com` (marketing), `app.topfuelauto.com` (web), `api.topfuelauto.com` (backend)

## Auth Storage
- Web stores JWT in localStorage for MVP (documented risk; move to httpOnly cookies later)
- Mobile stores token in secure storage when available

## Migrations
Run `alembic upgrade head` after containers start. Migration enables `unaccent` and `pg_trgm` and creates all tables.

## Worker
Celery worker runs via `docker compose` service `worker` with placeholder periodic task; extend for future jobs.