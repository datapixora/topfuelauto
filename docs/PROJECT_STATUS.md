# Project Status Summary

## Executive Summary
- Monorepo with FastAPI backend (`api/`), Next.js 14 web app (`web/`), Celery worker, Postgres, and Redis (see `docker-compose.yml`, `render.yaml`).
- JWT-based auth with shared secret resolution; login issues fixed and `/api/v1/auth/me` available (`api/app/core/security.py`, `api/app/routers/auth.py`).
- Search pipeline calls external MarketCheck provider via `/api/v1/search`, with caching, rate-limit guard, logging, and provider metadata (`api/app/routers/search.py`, `api/app/providers/marketcheck.py`).
- Search analytics logging upgraded with session, providers, cache/rate-limit flags; idempotent migration protects existing indexes (`api/app/models/search_event.py`, `api/migrations/versions/0004_search_event_analytics.py`).
- Admin metrics endpoints surface overview/search analytics; query field mismatches resolved and coalesce import fixed (`api/app/routers/admin.py`).
- Admin analytics UI rebuilt with charts, range filters, provider breakdown, and deduped API calls (`web/src/app/admin/search-analytics/page.tsx`).
- Web uses absolute API base from `NEXT_PUBLIC_API_BASE_URL`; admin requests include Bearer token (`web/src/lib/api.ts`, `web/src/lib/adminAnalytics.ts`).
- Landing page, login modal, QuickPulse health check, and soft-gated /search page shipped (`web/src/app/page.tsx`, `web/src/app/search/page.tsx`).
- Render blueprint deploys api/worker/web plus managed Postgres/Redis; CORS and env var guidance documented (`render.yaml`, `README.md`).
- Outstanding TODOs include search-plan enforcement, full pricing/signup, and redeploying with latest migration (see `TODO.md`).

## Completed Work List
- **Backend**
  - JWT consistency and `/api/v1/auth/me` (`api/app/core/security.py`, `api/app/routers/auth.py`).
  - MarketCheck provider adapter and aggregated search endpoint (`api/app/providers/marketcheck.py`, `api/app/routers/search.py`).
  - SearchEvent analytics fields, logging, and admin metrics fixes (`api/app/models/search_event.py`, `api/app/routers/admin.py`).
  - Idempotent migration guarding existing columns/indexes (`api/migrations/versions/0004_search_event_analytics.py`).
- **Frontend**
  - Landing/CTA polish, login dialog, QuickPulse health card (`web/src/app/page.tsx`, `web/src/components/system/QuickPulse.tsx`).
  - Search page wired to `/api/v1/search` with soft gate/pagination (`web/src/app/search/page.tsx`).
  - Admin analytics UI with charts/tables and deduped fetches (`web/src/app/admin/search-analytics/page.tsx`, `web/src/lib/adminAnalytics.ts`, `web/src/lib/api.ts`).
- **Infra/Docs**
  - Render blueprint for api/worker/web/postgres/redis (`render.yaml`).
  - Docker Compose for local stack (`docker-compose.yml`).
  - Encoding/CORS/API base guidance in `README.md` and `TODO.md`.

## What's Running in Production (from render.yaml)
- **API**: FastAPI (`api/app/main.py`) on Render web service `topfuelauto-api`; health at `/health`.
- **Worker**: Celery worker (`app/workers/celery_app.celery_app`) on Render worker service `topfuelauto-worker`.
- **Web**: Next.js app (`web/`) on Render web service `topfuelauto-web`, built via `npm run build`.
- **Data Stores**: Managed Postgres (`topfuelauto-db`) and Redis (`topfuelauto-redis`), wired via env vars (DATABASE_URL, CELERY_BROKER_URL/RESULT_BACKEND).
- **CORS/API Base**: `NEXT_PUBLIC_API_BASE_URL=https://api.topfuelauto.com/api/v1`, CORS origins set in `render.yaml`.

## Key Data Models and Migrations
- **Migrations**
  - `0001_init.py`: enables `unaccent`, `pg_trgm`; creates users, vehicles, listings (with search_tsv/text trigram indexes), price_history, broker_leads, vin_reports.
  - `0002_admin.py`: adds `users.is_admin`; creates `search_events` (initial fields) with indexes.
  - `0003_plans.py`: creates `plans` table with features/quotas JSONB and key index.
  - `0004_search_event_analytics.py`: adds session/query_raw/query_normalized/filters_json/providers/result_count/cache_hit/rate_limited/status/error_code plus indexes; idempotent guards for existing cols/indexes.
- **Models (api/app/models)**
  - `User`: email, password_hash, is_pro, is_admin, created_at.
  - `Plan`: key, name, description, price_monthly, features, quotas, is_active, created_at.
  - `Listing`/`Vehicle`/`PriceHistory`: core inventory with search text/tsvector.
  - `BrokerLead`: user/listing linkage with bid/contact fields.
  - `SearchEvent`: session_id, query_raw/normalized, filters_json, providers, result_count, latency_ms, cache_hit, rate_limited, status, error_code, timestamps.
  - `VinReport`: vin, report_type, payload_json.

## Backend Routers / Endpoints
- **Auth (`api/app/routers/auth.py`, prefix `/api/v1/auth`)**
  - `POST /signup`, `POST /login`, `GET /me`; JWT issued via `create_access_token`; guard `get_current_user`.
- **Search (`api/app/routers/search.py`, prefix `/api/v1`)**
  - `GET /search`: queries active providers (MarketCheck), supports make/model/year/price/location/sort/page/page_size; rate-limit + cache; logs SearchEvent; headers `X-Request-Id`, `X-Cache`.
- **Listings (`api/app/routers/listings.py`, prefix `/api/v1`)**
  - CRUD/read endpoints for listings (read path observed).
- **Broker (`api/app/routers/broker.py`, prefix `/api/v1`)**
  - Bid request and lead retrieval (auth required).
- **VIN (`api/app/routers/vin.py`, prefix `/api/v1`)**
  - Decode/history placeholders.
- **Admin (`api/app/routers/admin.py`, prefix `/api/v1/admin`)**
  - `GET /metrics/overview`, `GET /metrics/users`, `GET /metrics/subscriptions` (placeholder), `GET /metrics/searches` (top/zero queries, timeseries, providers, range filter), `GET /providers/status`, `GET /users/{id}`, `GET /subscriptions` (placeholder). Guarded by `get_current_admin`.
- **Admin Plans (`api/app/routers/admin_plans.py`, prefix `/api/v1/admin`)**
  - `GET /plans`, `PATCH /plans/{id}`; admin guard.

## Frontend (Next.js 14, App Router)
- **Landing**: `/` (`web/src/app/page.tsx`) with hero, QuickPulse health, value props.
- **Auth**: `/login`, `/signup`, `/account`, shared `LoginDialog/LoginForm` components.
- **Search**: `/search` (`web/src/app/search/page.tsx`) with filters, pagination, soft gate for unauthenticated users.
- **Pricing**: `/pricing` placeholder with plan cards.
- **Dashboard**: `/dashboard` placeholder with login redirect if no token.
- **Admin**: `/admin` layout plus pages for plans, providers, search analytics (charts/tables), subscriptions, users, user detail.
- **UI Stack**: Tailwind + shadcn-style components (Button/Card/Table/Dialog/Input/Alert), Recharts for analytics charts; API calls via absolute `apiGet` with Bearer token from localStorage `tfa_token`.

## Providers
- **MarketCheck** (`api/app/providers/marketcheck.py`):
  - Enabled when `MARKETCHECK_API_KEY`, `MARKETCHECK_API_SECRET`, and `MARKETCHECK_ENABLED` are set.
  - Base URL `MARKETCHECK_API_BASE` (default `https://mc-api.marketcheck.com/v2`).
  - Used by `/api/v1/search`; returns normalized listings with source metadata.

## Security / Auth Summary
- JWT secret resolved from env in priority: `JWT_SECRET` -> `SECRET_KEY` -> `APP_SECRET` (`api/app/core/config.py`).
- Tokens issued in `/api/v1/auth/login`; verified in `get_current_user`; admin guard returns 403 for non-admin.
- Web stores token in localStorage under `tfa_token`; API headers injected via `authHeaders`/`apiGet`.
- Rate-limiting on search endpoint (per-IP, in-memory); cache TTL 45s; logging records cache/rate-limited status.

## Known Resolved Issues
- Fixed admin metrics column mismatches (query_normalized/result_count) and coalesce import errors (`api/app/routers/admin.py`).
- Jose import error resolved in security module for Render compatibility (`api/app/core/security.py`).
- Migration 0004 made idempotent to avoid duplicate index errors on Render Postgres (`api/migrations/versions/0004_search_event_analytics.py`).
- Admin analytics requests deduplicated to avoid multiple `/metrics/searches` calls (`web/src/lib/api.ts`, `web/src/app/admin/search-analytics/page.tsx`).

## Next Steps (from TODO.md)
- Redeploy Render blueprint and rerun `alembic upgrade head` and seed scripts (plans), ensure env vars set (JWT_SECRET, ALLOWED_ORIGINS, NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_SITE_URL, ADMIN_EMAIL/PASSWORD).
- Connect /search to backend for live results/filters beyond MarketCheck aggregation.
- Implement full pricing page with Stripe plan selection and real signup flow.
- Add per-user usage tracking and plan enforcement for search; admin analytics endpoints/charts (remaining milestones).
