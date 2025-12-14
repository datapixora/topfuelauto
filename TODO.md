# TODO

1. [x] Base repo scaffolding: create required directory structure, .gitignore, and .env.example baseline.
2. [x] Backend core setup: FastAPI app skeleton, config, requirements, Dockerfile, Alembic config, health endpoint.
3. [x] Database models & migrations: define ORM models, enable extensions, create initial Alembic migration.
4. [x] API services & routers: auth (JWT), listings CRUD/read, search with ranking, VIN decode/history placeholder, broker leads, Celery worker/tasks.
5. [x] Seed data: implement scripts/seed_listings.py to load ~50 listings incl. Nissan GT-R 2005 variants.
6. [x] Web app scaffold: Next.js 14 + Tailwind structure, pages, components, API client/auth handling.
7. [x] Docker Compose: postgres, redis, api, worker, web wired for local run with env vars and volumes.
8. [x] Mobile scaffold: Flutter project with auth/search/listing/vin/broker flows using Riverpod + Dio.
9. [x] README: local setup, seed steps, production hosting notes (Render/Vercel/Cloudflare), domains/subdomains.
10. [x] Finalize: verify run flow, update TODO, git init/commit, push to GitHub main.
11. [x] Fix Render blueprint envVar sources and redis ipAllowList.
12. [x] Fix legacy Postgres plan (Render) to supported tier.
13. [x] Fix Render web build (lockfile).
14. [x] Fix non-UTF8 web file (search page) for Render build.
15. [x] Fix /search suspense CSR bailout.
16. [x] Pin Render Python version to 3.12 to avoid pydantic-core build.
17. [x] Add email-validator for EmailStr.
18. [x] Web homepage renders UI on "/" and pings API using NEXT_PUBLIC_API_BASE_URL.
19. [x] Add docs for Render custom domain + CORS + env vars.
20. [x] Ensure web uses NEXT_PUBLIC_API_BASE_URL only and pings /api/v1/health with clear missing-env message.
21. [x] Fixed API base URL join (no duplicate /api/v1) and removed any domain hardcoding.
22. [x] Added /api/v1/health endpoint and aligned web health check.
23. [x] API health available at /api/v1/health (and /health alias kept).
24. [x] Fixed health router import and ensured /api/v1/health works.
25. [x] CORS locked to final domains.
26. [x] Documented web env vars for migration (API base + site url).
27. [x] Added admin dashboard UI + pages, admin metrics endpoints, and search event logging.
28. [x] Fix admin build error (table colSpan typing).
29. [x] Admin fetches include auth token and handle 401.
30. [x] Auth foundations (login + admin access).
31. [x] ChatGPT-friendly README/guide (pending after revert).
32. [x] Login now returns 401 (not 500) on bad credentials.
33. [x] Admin bootstrap user script added.
34. [x] Fix SQLAlchemy model registry import (BrokerLead) for scripts.
35. [x] Fix Alembic revision chain (0001_init present and referenced by 0002_admin).
36. [x] Pin bcrypt/passlib compatible versions and backend check.
37. [x] User subscription page UI.
38. [x] Admin plans edit wired to API (UI).
39. [x] Replace temporary /api/v1/admin/plans with DB-backed model, migration, and seed script.
40. [ ] Redeploy Render Blueprint, run `alembic upgrade head` and `python scripts/seed_plans.py`, set env vars (JWT_SECRET, ALLOWED_ORIGINS, NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_SITE_URL, ADMIN_EMAIL, ADMIN_PASSWORD), confirm web/admin works and /api/v1/health passes.
41. [x] Polish admin plans UI (cards, feature/quota labels, better edit UX).
42. [x] Rebuilt marketing homepage with hero, search preview UI, value props, FAQ, and navigation with login modal plus dashboard/signup placeholders.
43. [x] Added shared login form/dialog tied to updated auth client storing token in `tfa_token` and redirecting to /search.
44. [x] Implement QuickPulse health check (client ping + latency + retry + timeout).
45. [x] Home polish pass (CTA copy, nav UX, pricing/dashboard placeholders, FAQ clarity).
46. [ ] Connect /search to backend for live results and filters.
47. [ ] Implement full pricing page and Stripe plan selection.
48. [ ] Implement real signup flow (UI + API).
49. [ ] Add admin dashboard analytics visualizations.
50. [x] Add MarketCheck provider adapter and /api/v1/search aggregation endpoint.
51. [x] Wire /search page to MarketCheck with soft-gate and pagination.
52. [x] Add per-user usage tracking and plan enforcement for search.
53. [ ] Add admin analytics charts for search usage.
54. [x] Ensure admin plans endpoint works after quota fields (auto-run Alembic on Render start).
- [x] Fix admin API base URL for analytics (use NEXT_PUBLIC_API_BASE_URL).
- [x] Fix JWT verify consistency (admin 401) and add /api/v1/auth/me.
- [x] Fix jose import error on deploy (security module).
- [x] Fix admin metrics analytics query field.
- [x] Fix admin metrics 500s (SearchEvent field mismatch).
- [x] Fix SQLAlchemy coalesce import in admin metrics.
- [x] Make search_event_analytics migration idempotent (columns/indexes guard).
- [x] Milestone 3: Admin search analytics UI (charts, range filters).
- [x] Deduplicate admin search analytics requests (single fetch per range).

## Analytics Milestones
- [x] Milestone 1: Harden SearchEvent logging (fields, caching/rate-limit signals, safe errors).
- [ ] Milestone 2: Admin analytics endpoints (overview, timeseries, top queries, zero-results, provider health).
- [ ] Milestone 3: Admin analytics UI (cards, charts, tables).
