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
33. [ ] Redeploy Render Blueprint, run migrations (including 0002_admin), set env vars (JWT_SECRET, ALLOWED_ORIGINS, NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_SITE_URL), confirm web/admin works and /api/v1/health passes.
