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
5) Visit web at http://localhost:3000 and search "Nissan GT-R 2005" (API at http://localhost:8000)

## Render Deployment (blueprint)
1) Connect the repo on Render as a Blueprint and point to `render.yaml` (root).
2) Deploy; Render provisions Postgres + Redis + three services (api, worker, web).
3) In the Render Dashboard, set a single `JWT_SECRET` value and confirm `CORS_ORIGINS=https://app.topfuelauto.com,http://localhost:3000` on the API service (set the same secret on the worker).
4) After first deploy, open a shell on the **api** service and run `cd api && alembic upgrade head` to apply migrations.
5) (Optional) Seed sample data from the same shell: `python scripts/seed_listings.py`.
6) Attach custom domains: `api.topfuelauto.com` to the api service, `app.topfuelauto.com` to the web service. Ensure HTTPS certs issue, then keep CORS origins aligned with those domains.

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

## Hosting Plan (Render)
- API (FastAPI) + worker (Celery) + web (Next.js) all run on Render via `render.yaml`.
- Managed Postgres and Redis are provisioned through the blueprint.
- Primary domain: `topfuelauto.com`; working subdomains: `app.topfuelauto.com` (web), `api.topfuelauto.com` (API).
- Optional: `tupfuelauto.com` redirect handled via DNS provider/Cloudflare if desired later.

## Auth Storage
- Web stores JWT in localStorage for MVP (documented risk; move to httpOnly cookies later)
- Mobile stores token in secure storage when available

## Admin Access
- Log in at `/login` (or `/account`) to obtain a JWT.
- Promote the user to admin in Postgres (Render shell → `cd api`):
  ```sql
  UPDATE users SET is_admin = true WHERE email = 'admin@example.com';
  ```
- Re-login so the stored token is fresh, then open `/admin`.

## Migrations
Run `alembic upgrade head` after containers start (local) or from a Render shell on the api service (`cd api && alembic upgrade head`). Migration enables `unaccent` and `pg_trgm` and creates all tables.

## Worker
Celery worker runs via `docker compose` service `worker` (and Render worker) with placeholder periodic task; extend for future jobs.

## Required Environment Variables
- API/Worker: `DATABASE_URL` (from Render Postgres), `CELERY_BROKER_URL` + `CELERY_RESULT_BACKEND` (from Render Redis), `JWT_SECRET`, `ALLOWED_ORIGINS`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `NHTSA_API_BASE` (default provided).
- Web:  
  - `NEXT_PUBLIC_API_BASE_URL` (e.g., `https://api.topfuelauto.com/api/v1` on Render today; later Vercel can point to the same).  
  - `NEXT_PUBLIC_SITE_URL` (optional, e.g., `https://topfuelauto.com`) — use if you need absolute links.

## Encoding Note
Ensure source files are saved as UTF-8 (no UTF-16/BOM from some Windows editors), otherwise Next.js builds on Render will fail on read.
