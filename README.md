# TopFuel Auto — Dev Guide (ChatGPT-friendly)

Search-first marketplace MVP (FastAPI + Next.js + Flutter).

## Quickstart (local)
1) cp .env.example .env
2) docker compose up --build
3) docker compose exec api alembic upgrade head
4) docker compose exec api python scripts/seed_listings.py
5) Web http://localhost:3000  |  API http://localhost:8000

## Deploy on Render (blueprint)
- Use render.yaml (api, worker, web, Postgres, Redis).
- API/worker env: DATABASE_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND, JWT_SECRET, ALLOWED_ORIGINS, NHTSA_API_BASE.
- Web env: NEXT_PUBLIC_API_BASE_URL=https://api.topfuelauto.com/api/v1 (or your API URL); optional NEXT_PUBLIC_SITE_URL=https://topfuelauto.com.
- After first deploy: run `cd api && alembic upgrade head` in API shell; optional seed script.
- Add custom domains in Render; wait for SSL.

## Auth & Admin
- Login at /login (or /account). Token stored in localStorage (MVP).
- Make an admin: UPDATE users SET is_admin=true WHERE email='you@example.com'; then re-login.
- Admin area: /admin (requires admin JWT).

## API Map
- Health: GET /api/v1/health (alias /health)
- Auth: POST /api/v1/auth/signup | login | GET /api/v1/auth/me
- Listings: GET /api/v1/listings, /api/v1/listings/{id}
- Search: GET /api/v1/search?q=...
- VIN: GET /api/v1/vin/decode | /vin/history (Pro placeholder)
- Broker: POST /api/v1/broker/request-bid | GET /api/v1/broker/leads/me
- Admin (requires admin): /api/v1/admin/metrics/*, /admin/providers/status

## Data & Search
- Postgres extensions: unaccent, pg_trgm
- search_text + search_tsv, ranking mixes ts_rank + trigram
- Search events logged to search_events for analytics

## Worker
- Celery worker via docker compose & Render worker; placeholder beat task.

## Encoding
- Keep source files UTF-8 (no UTF-16/BOM) to avoid Next.js build errors.