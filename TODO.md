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
49. [x] Fix admin provider toggles not affecting /search endpoint - providers disabled in admin now correctly excluded from execution and reported as disabled in sources response.
50. [x] Complete provider config system fix - removed hardcoded exclusions, removed marketcheck failsafe, changed provider modes to 'both' to enable all providers for search/assist via admin panel.
51. [ ] Add admin dashboard analytics visualizations.
50. [x] Add MarketCheck provider adapter and /api/v1/search aggregation endpoint.
51. [x] Wire /search page to MarketCheck with soft-gate and pagination.
52. [x] Add per-user usage tracking and plan enforcement for search.
53. [ ] Add admin analytics charts for search usage.
54. [x] Ensure admin plans endpoint works after quota fields (auto-run Alembic on Render start).
55. [x] Search UI shows quota status and upgrade CTA on limit.
56. [x] Data Engine STEP 1: Database schema - created tables (admin_sources, admin_runs, staged_listings, staged_listing_attributes, merged_listings, merged_listing_attributes), Alembic migration, SQLAlchemy models, Pydantic schemas, and basic CRUD service functions.
57. [x] Data Engine STEP 2: Admin API endpoints - created FastAPI router with CRUD endpoints for sources, runs, and staged listings. All endpoints require admin auth. No scraping yet.
58. [x] Data Engine STEP 3: Admin UI - created Next.js admin pages (/admin/data/sources list, /admin/data/sources/[id] details, /admin/data/runs/[runId] progress view). Card-based UI with enable/disable toggles, delete confirmations, run history, and staged items preview.
59. [x] Data Engine STEP 4: Proxy Settings - added crypto_service.py (Fernet encryption for sensitive data with ENCRYPTION_KEY env var), updated data_engine_service to auto-encrypt/decrypt proxy credentials in settings_json (proxy_username, proxy_password), added POST /admin/data/test-proxy endpoint for connectivity testing, created /admin/data/sources/new page with full source creation form including proxy configuration (URL, auth, type, test button with latency display), and added cryptography==42.0.5 to requirements.txt.
60. [x] Data Engine STEP 5: Scrape Engine Integration - created data_engine.py Celery worker with run_source_scrape task (creates AdminRun, executes scraping with rate limiting/pagination/proxy support, stores items in staged_listings, handles failures with exponential backoff and auto-disable after 5 failures), added enqueue_due_sources scheduler task to celery beat (runs every 3min), added POST /admin/data/sources/{id}/run endpoint for manual run triggering. List-only mode implemented (no detail page follows yet). Placeholder parser returns empty list (source-specific parsers needed for actual extraction).
61. [x] Data Engine STEP 6: Review Queue + Manual Merge - added approve/reject API endpoints (POST /admin/data/staged/{id}/approve merges to merged_listings with attributes copy and deletes staged, POST /admin/data/staged/{id}/reject deletes without merging), bulk actions (POST /admin/data/staged/bulk-approve and bulk-reject with error tracking), created /admin/data/staged page UI (card-based staging queue with checkbox selection, individual approve/reject buttons, bulk action toolbar, attribute expansion, source link, status badges), added 5 API client functions to api.ts. Full manual review workflow implemented.
62. [x] Data Engine STEP 7: Auto-Merge Rules - added per-source merge_rules JSON (auto_merge_enabled, require year/make/model, require price/url, optional min_confidence), confidence_score + auto_approved fields on staged/merged listings, updated scraper to auto-approve (not auto-merge) items that pass rules, and exposed merge rule editor in admin UI plus auto-approved bulk action. Runs now track auto_approved counts and leave items in staging for manual merge trigger.
56. [x] User signup MVP (email/password) live.
57. [x] Fix quota decrement only on non-zero results.
58. [x] Fix quota banner loading state and persistence on return.
59. [x] Admin quota funnel analytics with upgrade candidates.
60. [x] Admin user management v1 (plan changes, deactivate/reactivate).
61. [x] Admin user detail cockpit (quota, usage, searches, actions).
62. [x] Remove is_pro as source of truth (plan-based enforcement).
63. [x] Stripe v1 monthly+yearly (admin-config) checkout + webhook.
64. [x] Assist Core v1 with watch mode and prompt skeleton.
65. [x] Hotfix: import ForeignKey for user current_plan_id to fix deploy.
66. [x] Fix admin metrics users 500/CORS symptom.
67. [x] Watch scheduler (beat) enqueues due watch cases with plan guards + enqueue lock.
68. [x] User navigation/auth UX improved (header login state + dashboard link + logout).
69. [x] Alerts v1 (saved searches + in-app notifications + scheduling).
70. [x] Assist market.scout now uses real search/provider (quota + signature delta).
71. [x] Authenticated web calls send Bearer headers; /auth/me & assist submit handle 401 with clean login redirect/CORS-safe.
72. [x] search_events.query now always populated; analytics logging is non-fatal to prevent Assist/Search 500s.
73. [x] Admin provider manager added; provider_settings table controls enabled/priority/mode; search & assist honor enabled providers with marketcheck fallback.
74. [x] Fixed Alembic multiple-heads error by merging provider_settings branch with main migration head.
75. [x] Provider Manager stabilized with seeded defaults (marketcheck on, copart_public off) and fail-safe gating.
76. [x] Added server-side search cache (15m TTL) schema/service for faster repeated queries.
77. [x] Step 2.1: Search endpoint uses 15m DB cache (quota-safe, non-fatal); cache hits do not consume quota.
78. [x] Step 3A: Added copart_public provider for Assist market.scout (public-only, admin-togglable, fail-safe).
79. [x] Market.scout step now records provider debug (requested/enabled/executed counts & errors) to trace copart usage.
80. [x] Added market.scout debug metadata (queries, filters, signatures, providers, counts) to investigate duplicate results.
81. [x] Added market.scout debug section (query, filters, providers, counts, signature, cache) into step/report to diagnose constant results.
82. [x] Fixed market.scout query selection to use vehicle info or case title instead of constant \"car search\" fallback.
83. [x] Fix AssistStep JSON serialization (quota/output_json) + load steps for validation.
84. [x] Implement query parser to extract structured filters (make/model) from free-text queries for better MarketCheck results.
85. [x] Fix search normalization critical bugs: priority rules, MarketCheck q parameter omission, cache key includes final filters.
86. [x] Add provider capability gating (requires_structured, supports_free_text) to skip MarketCheck without make/model and prevent garbage results.
87. [x] Harden CopartPublicProvider to handle non-JSON responses (HTML/Cloudflare blocks/403/empty) with status/content-type validation, retries, and graceful error handling.
88. [x] Add production-ready legal pages: Terms of Service, Privacy Policy, Data Sources & Disclaimer, DMCA/Takedown + footer links + backend API endpoints (versioned legal documents).
89. [x] Add on-demand crawl search provider + Celery job + UI polling.
90. [x] Data Engine: detect Incapsula/Imperva blocks (short HTML, _Incapsula_Resource, robots noindex) and mark runs BLOCKED with diagnostics; plan to use legal provider/API for Copart or keep source disabled for MVP.
91. [x] Data Engine: add block diagnostics (status_code, final_url, html_len, proxy_used), per-source cooldown (auto-pause 6h after 2 blocks/30m), cache duplicate signatures to avoid repeat hits, surface cooldown/last block in admin UI.
92. [x] SmartProxy hardening: rotate session-based proxy credentials + user agents, cache signatures 10m to reduce hits, and keep bot-block handling (no bypass).
93. [x] Fix proxy config and classify proxy failures: env-driven SmartProxy URL, masked creds, proxy health check (ipify), proxy_failed status with cooldown, UI badges.
94. [x] Admin Proxies tab + DB-managed pool: CRUD + health checks, encrypted passwords, proxy-weighted selection in Data Engine, run-level proxy diagnostics, UI pool metrics.
95. [x] Fix admin overflow for long URLs/JSON (base URL break, copy + toggle, settings JSON container).
96. [x] BUGFIX (PROD): Fix ProxyMode enum SQLAlchemy decode error - updated enum to use uppercase values (NONE/POOL/MANUAL), modified migration 0020 to create uppercase enum, added migration 0021 to convert existing lowercase values, added Pydantic validators to normalize inputs, and comprehensive regression tests.
97. [x] HOTFIX (PROD): Fix migration 0021 Postgres enum safety - use autocommit_block for ADD VALUE operations to avoid "unsafe use of new value" error. Migration now commits enum values before using them in UPDATE statements, fixing API and worker crashes.
98. [x] ARCHITECTURE FIX: Wire Data Engine Sources to Proxy Pool - removed duplicate proxy config system (manual host/port/user/pass fields) from Data Engine Source form. Sources now use proxy_mode (NONE/POOL) and proxy_id to reference centralized Proxy Pool. Added GET /api/v1/admin/proxies/options endpoint call, proxy dropdown UI with health status indicators, and warning when no proxies configured. Proxy credentials now stored only in Proxy Pool (single source of truth).
99. [x] COMPREHENSIVE PATCH: Four critical production fixes - (1A) Fixed DELETE /admin/data/sources/{id} 500 error with proper error handling and logging, (1B) Added global exception handlers to ensure CORS headers on all error responses (500/404/422), (2) Fixed proxy application in Data Engine runner - proxy_mode=POOL now correctly uses source.proxy_id to fetch and apply proxy from pool with detailed logging, (3) Fixed false BLOCKED classification - rewrote _detect_block() to be conservative (never marks status=200 as blocked, requires strong evidence like Incapsula/Imperva/Cloudflare/captcha indicators, only blocks 403/429/503 with short HTML <1000 chars), (4) Fixed pages_planned=0 division errors - updated AdminRun model default from 0 to 1, worker enforces max(source.max_pages_per_run, 1), created migration 0022 to update existing data and column default. Includes comprehensive regression tests covering all four issues.
100. [x] RELEASE TRACKING: Added GET /api/v1/meta endpoint returning git_sha and build_time from env vars (GIT_SHA, BUILD_TIME). API and Worker log git_sha on startup for deployment verification. Created DEPLOYMENT.md with instructions for setting env vars in Render, verification steps, and troubleshooting. Helps confirm production is running expected commit (suspected worker not deployed to 787467b due to proxy_used=false and BLOCKED on status=200 still occurring).
101. [x] FIX CASCADE DELETE: Fixed DELETE /admin/data/sources/{id} returning 409 "null value in column source_id violates not-null constraint". Root cause: SQLAlchemy ORM tries to SET NULL on child FKs before deleting parent, but source_id is NOT NULL. Solution: (1) Changed delete_source to use SQLAlchemy Core DELETE statement (bypasses ORM relationship handling and lets DB CASCADE work), (2) Added passive_deletes=True to all relationships (AdminRun.source, StagedListing.run, StagedListing.attributes, StagedListingAttribute.listing) to prevent ORM from trying to NULL FKs in other code paths, (3) Created migration 0023_fix_cascade using DROP CONSTRAINT IF EXISTS + op.create_foreign_key with ondelete="CASCADE" for three FK chains. Migration is idempotent. Updated router to catch IntegrityError and return 409. Added comprehensive regression tests (6 test cases). Proper status codes: 204 on success, 404 if not found, 409 if constraint violation (should not happen).
102. [x] DEBUG CAPTURE & BLOCK DETECTION FIX: Fixed false "blocked" classification for sources like force-ecu.com/eshop. Implemented comprehensive page debug capture: every fetched page now stores status_code, final_url, elapsed_ms, content_type, server/location headers, body_len, body_snippet_200 (first 200 chars), block_reason, proxy_used, error string in run.debug_json under debug.pages[]. Updated _detect_block() to ONLY mark blocked on HTTP status {401,403,429,503} OR body matches block keywords (incapsula, imperva, cloudflare challenge, captcha, access denied, blocked by, rate limit) - NO LONGER marks blocked just because items==0 or selector returned nothing. block_reason format: "http_status:<code>", "keyword_match:<keyword>", "exception:<type>". Added debug mode support: set source.settings_json["debug"]=true to temporarily disable auto-pause cooldown during debugging. Debug info stored in AdminRun.debug_json for admin UI display.
103. [x] Data Engine: Auto-Detect for Sources - added POST /api/v1/admin/data/sources/{id}/detect (httpx first, optional proxy + Playwright fallback), rule-based fingerprints/candidate strategies, persisted detect_report + detected_strategy to source.settings_json, and added admin UI panel to run detect and apply a chosen strategy.
104. [x] Data Engine: Generic HTML Extractor Template - added POST /api/v1/admin/data/sources/{id}/test-extract to fetch HTML and preview parsed items (generic_html_list). Added admin UI Extractor Template panel to edit selectors, test extract without saving, and save extract config to source.settings_json.extract.
105. [x] Data Engine: Normalize Source Settings - introduced settings_json.targets.test_url (used by detect + test-extract), settings_json.fetch (use_proxy/use_playwright/timeout_s/headers), standardized settings_json.extract schema (strategy/list/fields/normalize), detect now returns suggested_settings_patch + UI button to apply it.
106. [x] Data Engine: Safe Save Template - added POST /api/v1/admin/data/sources/{id}/save-template to validate extractor config (must find items) before persisting settings_json.extract, settings_json.targets.test_url, and settings_json.extract_sample (tested_at/url/items_preview); UI Save Template calls save-template, shows “Saved ✓”, and offers a Run Now CTA.
107. [x] Data Engine: Detect → Template → Test flow polish - single settings_json.targets.test_url used by Detect/Test Extract/Save, multi-strategy Detect (jsonld_product/jsonld_itemlist/shopify/woocommerce/nextjs/generic_html_list) now returns non-placeholder suggested_settings_patch, Apply Suggested Template auto-triggers a Test Extract preview, and runner uses settings_json.extract template to stage items (plus deep-merge settings_json.targets/fetch to avoid clobbering nested keys).
108. [x] Data Engine: Detect v2 strengthened (PAUSED / EXPERIMENTAL) - multi-attempt fetch matrix (httpx/proxy/playwright), robust signals (jsonld_count/types + platform scores + card/pagination scores), chosen_best attempt surfaced in UI, and unit tests for jsonld/woocommerce/shopify/generic card pages.
109. [x] Data Engine: WooCommerce suggested template improvements (PAUSED / EXPERIMENTAL) - dedicated WooCommerce selector builder (no empty selectors), stronger card-scoring guardrails to avoid page-level containers, editable suggested template UI with apply+auto Test Extract, and updated tests.
110. [ ] Data Engine: Template Library (presets-first) - build manual + preset-based templates (WooCommerce / Shopify / Generic HTML) and prioritize Template → Run → Stage → Review pipeline before revisiting Auto-Detect.
111. [x] CSV IMPORT FEATURE: Comprehensive CSV upload/import system for Admin UI. Backend: admin_imports table (status tracking, progress counters, column mapping, preview data), import_service (CSV parsing, header detection, suggested mapping heuristics), upload endpoint (multipart/form-data with preview + suggested mapping), Celery import_processor task (streaming CSV, robust field parsing for price/mileage/dates, upserts to merged_listings with idempotency by source_key+URL, batch commits every 500 rows, error tracking). Frontend: /admin/imports page with drag & drop upload, live preview table, column mapping UI, real-time progress tracking (polling), completion summary (created/updated/skipped/errors), error log display, recent imports list. Search Integration: InternalCatalogProvider queries merged_listings (free-text + structured filters), 7 performance indexes on merged_listings (price, status, created_at, location, sale_datetime, make+model+year composite, status+created composite), auto-seeded in provider_settings (priority 10). Features: idempotent (SHA256 dedup + URL-based upsert), robust parsing (handles $, commas, date formats), production-safe (transactional batching, validation, graceful errors), imports immediately searchable in /search alongside external providers. Tested with 1000-row Copart CSV. BUGFIX: Fixed Button component variant type error (replaced variant="outline" with variant="ghost", removed unsupported size prop) - web build now passes.
112. [x] INTERNAL-FIRST SEARCH: Switched public search from external-first to internal DB-first without breaking production. Configuration: Added SEARCH_INTERNAL_FIRST (default: true), SEARCH_INTERNAL_MIN_RESULTS (default: 1), SEARCH_EXTERNAL_FALLBACK_ENABLED (default: false) to config.py. Search Logic: Modified /api/v1/search endpoint to query internal_catalog provider FIRST, only query external providers (MarketCheck, Copart) if internal results < threshold AND fallback enabled. Backward Compatible: Setting SEARCH_INTERNAL_FIRST=false reverts to old behavior (query all providers). Production Safe: External fallback disabled by default, internal-first enabled by default. Logging: Comprehensive logs for internal results count, fallback triggers, skipped providers. Skip Reasons: External providers marked as "skipped" with reason "internal_first_sufficient" when internal returns enough results. Testing: Created test_internal_first_search.py with 6 test cases covering: internal-first with results (external skipped), internal-first with fallback (external queried), internal-first disabled (old behavior), fallback disabled (external never queried), config defaults (production-safe). Result: Imported CSV listings now appear as primary search results, external APIs used only as optional fallback. No UI changes required - same /search endpoint. BUGFIX: Created merge migration (0027_merge_heads) to resolve "Multiple head revisions" Alembic error caused by parallel branches (0025_merged_search_idx + 0025_public_plans_fields both descending from 0024_admin_imports).

113. [x] Marketing homepage pricing cards now come from Admin Plans (public /api/v1/public/plans + ISR revalidate=300); no hardcoded copy on "/".
114. [x] Landing Plans section CTA is auth-aware (no /login redirect when already logged in) and design refreshed with "Most Popular" emphasis + #plans anchor scroll.
115. [x] Admin: added Search Fields registry UI (/admin/search/fields) to manage dynamic search_fields (CRUD + toggles).
116. [x] BIDFAX SOLD RESULTS PIPELINE: Comprehensive auction data ingestion system for pricing intelligence. Database: auction_sales table (VIN/lot_id/auction_source/sold_price with JSONB attributes), auction_tracking table (crawler state with retry/backoff logic), migration 0029 with composite unique constraint (vin, auction_source, lot_id) for deduplication. Backend: BidfaxHtmlProvider with BeautifulSoup (rate limiting 30 req/min, realistic headers, robust parsing for VIN/price/lot/status/date/odometer/damage/condition), SoldResultsIngestService with PostgreSQL UPSERT (ON CONFLICT DO UPDATE), Celery tasks (enqueue_bidfax_crawl creates tracking rows, run_tracking_batch beat scheduler every 5min, fetch_and_parse_tracking with exponential backoff 2^attempts minutes capped at 24h). API: 6 admin endpoints (/jobs, /tracking, /tracking/{id}/retry, /auction-sales, /test-parse, /listings/{id}/sold-results) requiring admin auth. Frontend: /admin/data/sold-results page with Create Crawl Job form (URL/pages/make/model/schedule), status overview cards (pending/running/done/failed counts), Test URL Parse tool (quick validation without saving), tracking table with retry buttons, color-coded status indicators. Features: idempotent (unique constraint prevents duplicates), resumable (status transitions pending→running→done/failed), scheduled crawls with next_check_at, JSONB storage for flexible fields (attributes, raw_payload, stats), provider abstraction for future sources (Copart/IAAI), comprehensive unit tests (15 test cases for HTML parsing/price/odometer/date), block detection with conservative false-positive prevention, admin-only access. Use case: enables Expected Sold Price ML model and Deal Score calculation by providing historical auction price data joined to listings by VIN/lot_id.

## is_pro removal audit
- [x] api/app/routers/auth.py uses plan resolver (is_pro deprecated only)
- [x] api/app/routers/search.py uses plan resolver
- [x] api/app/routers/admin.py removed is_pro usage
- [x] api/app/routers/vin.py uses plan resolver
- [x] api/app/schemas/auth.py marks is_pro deprecated
- [x] api/app/schemas/user.py marks is_pro deprecated
- [x] api/app/models/user.py defines is_pro (legacy only, not used)
- [x] web/src/app/admin/users/page.tsx uses plan info
- [x] web/src/app/admin/users/[id]/page.tsx uses plan info

Next steps:
- [ ] Admin: refund/credit tools (future)
- [ ] Stripe sync: plan changes via webhook (later)
- [ ] Show subscription status in user account
- [ ] Handle proration / upgrades / downgrades
- [ ] Webhook coverage for subscription updates
- [ ] Wire real OpenAI/DeepSeek providers
- [x] Add watch scheduler beat + alerts
- [ ] Budget enforcement for Assist calls
- [ ] Alerts v2: email/push delivery and richer dedupe

Next steps:
- [ ] Add conversion tracking: upgrades after quota hit
- [ ] Email/notification outreach to upgrade candidates
- [ ] Feature gating v1

Next steps:
- [ ] Password reset flow
- [ ] Email verification
- [ ] Anonymous-to-user conversion
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


## Milestone #113: Search Field Registry + JSONB Extra Storage

**Status**: ✅ Complete
**Completion Date**: 2025-12-17

### Overview
Implemented a dynamic search field registry system that allows adding new searchable fields without database migrations. Fields can be stored in core columns or JSONB extra storage, making the system extensible for CSV imports with custom columns.

### Features Implemented

#### Database Changes (Migration 0028)
- ✅ Added `merged_listings.extra` JSONB NOT NULL DEFAULT '{}'
- ✅ Added `merged_listings.raw_payload` JSONB for backfill capability
- ✅ Created `search_fields` table with configuration:
  - `key`, `label`, `data_type`, `storage` (core|extra)
  - `enabled`, `filterable`, `sortable`, `visible_in_search`, `visible_in_results`
  - `ui_widget`, `source_aliases` JSONB, `normalization` JSONB
- ✅ Added GIN index on `merged_listings.extra` for fast JSONB queries
- ✅ Seeded 14 fields (6 core: year, make, model, price, mileage, location; 8 extra: vin, damage, title_code, cylinders, transmission, fuel_type, body_style, color)

#### Backend Implementation
- ✅ Created `SearchField` model with full field configuration
- ✅ Created search_field schemas with slug-like key validation
- ✅ Admin CRUD API endpoints:
  - `GET /api/v1/admin/search/fields` - List all fields
  - `POST /api/v1/admin/search/fields` - Create new field
  - `PATCH /api/v1/admin/search/fields/{id}` - Update field
  - `DELETE /api/v1/admin/search/fields/{id}` - Delete field
- ✅ Public API endpoint:
  - `GET /api/v1/search/fields` - Get enabled fields for search UI
- ✅ Updated import processor to use registry:
  - Maps CSV headers via `source_aliases` array
  - Writes to core columns or `extra` JSONB based on `storage` field
  - Stores entire CSV row in `raw_payload` for backfill
  - No longer stores in `merged_listing_attributes` table
- ✅ Created `backfill_extra_fields` Celery task:
  - Can filter by import_id or date range
  - Reprocesses `raw_payload` through current registry
  - Updates `extra` JSONB with newly enabled fields

#### Frontend
- ✅ Added "Search Fields" link to admin navigation menu

### Benefits
1. **No DB Migrations for New Fields**: Admin can create new searchable fields via API
2. **CSV Columns Preserved**: Fields like "Cylinders" now stored and searchable
3. **Backfill Capability**: Historical imports can be reprocessed with new fields
4. **Type-Safe Parsing**: Data types (integer, string, decimal, date) enforced
5. **Flexible Mapping**: Multiple CSV header aliases per field
6. **Storage Strategy**: Core fields in dedicated columns, extras in JSONB

### Example Usage

#### Creating a New Field
```bash
POST /api/v1/admin/search/fields
{
  "key": "engine_size",
  "label": "Engine Size",
  "data_type": "decimal",
  "storage": "extra",
  "enabled": true,
  "filterable": true,
  "sortable": true,
  "source_aliases": ["Engine Size", "engine_size", "displacement"],
  "ui_widget": "range"
}
```

#### Backfilling Historical Data
```python
from app.workers.import_processor import backfill_extra_fields

# Backfill all listings from specific import
backfill_extra_fields.delay(import_id=123)

# Backfill all listings in date range
backfill_extra_fields.delay(start_date="2025-01-01", end_date="2025-12-31")
```

#### Querying Extra Fields
```sql
-- Find cars with 8 cylinders
SELECT * FROM merged_listings WHERE extra->>'cylinders' = '8';

-- Find cars with manual transmission
SELECT * FROM merged_listings WHERE extra->>'transmission' ILIKE '%manual%';
```

### Technical Notes
- GIN index on `extra` enables fast JSONB queries
- `raw_payload` stored as-is for future backfill (no normalization)
- `source_aliases` checked in order (first match wins)
- Import processor loads registry once per import (not per row)
- Backward compatible with old `column_map` format

### Testing
- ✅ Migration runs successfully (0028_search_field_registry.py)
- ✅ Import processor uses registry for field mapping
- ✅ CSV imports write to `extra` JSONB correctly
- ✅ Admin API validates key format (slug-like)
- ✅ Public API returns only enabled fields
- ⏳ TODO: Add frontend UI for managing search fields in admin panel

### Related
- Fixes imports getting stuck at 0/166 (Celery task registration)
- Enables dynamic search filters in future UI updates
- Foundation for admin-configurable search experience


### Bugfix: ResponseValidationError in GET /api/v1/admin/search/fields
**Date**: 2025-12-17
**Issue**: Endpoint returned 500 error due to datetime serialization mismatch  
**Root Cause**: Pydantic schema expected `created_at`/`updated_at` as `str`, but SQLAlchemy returned `datetime` objects

**Fix Applied**:
- Changed `SearchFieldResponse.created_at` and `updated_at` from `str` to `datetime` type
- Imported `datetime` in search_field.py schemas
- Removed redundant `orm_mode` (Pydantic v2 uses `from_attributes` only)
- Added comprehensive test suite (`test_admin_search_fields.py`) with 5 test cases:
  - ✅ `test_list_search_fields_success` - Validates 200 + proper datetime serialization
  - ✅ `test_get_search_field_by_id` - Single field retrieval
  - ✅ `test_create_search_field` - POST new field  
  - ✅ `test_create_field_invalid_key` - Validation error handling
  - ✅ `test_list_fields_without_auth_fails` - Auth protection

**Result**: Endpoint now properly serializes SQLAlchemy datetime objects to ISO format strings in JSON responses.


## Login Page Redirect for Authenticated Users
**Date**: 2025-12-18
**Feature**: Prevent authenticated users from seeing the login form by redirecting them immediately

### Implementation
- Added `getCurrentUser()` API function in `web/src/lib/api.ts` that calls `/auth/me` without auto-redirect on 401
- Created `getNextUrl()` helper in `web/src/lib/utils.ts` to safely validate the `next` query parameter (prevents open redirect vulnerabilities)
- Updated `web/src/app/login/page.tsx` to:
  - Check authentication status on mount using token + `/auth/me` call
  - Show "Checking session..." loading state while verifying auth
  - Redirect authenticated users to:
    - The `next` query parameter (if valid and same-origin)
    - `/admin` for admin users (when no `next` parameter)
    - `/dashboard` for regular users (when no `next` parameter)
  - Clear invalid tokens and show login form for unauthenticated users
  - Prevent form flicker by rendering loading state until auth check completes

### Manual QA Checklist
- [ ] **Unauthenticated user**: Visit `/login` → should see login form immediately (no redirect)
- [ ] **Authenticated regular user**: Visit `/login` → should redirect to `/dashboard` (no form shown)
- [ ] **Authenticated admin user**: Visit `/login` → should redirect to `/admin` (no form shown)
- [ ] **With valid next param**: Visit `/login?next=/account/alerts` → should redirect to `/account/alerts` after auth check
- [ ] **With invalid next param (external)**: Visit `/login?next=https://evil.com` → should redirect to default page (not external site)
- [ ] **With invalid next param (protocol-relative)**: Visit `/login?next=//evil.com` → should redirect to default page
- [ ] **With invalid next param (javascript)**: Visit `/login?next=javascript:alert(1)` → should redirect to default page
- [ ] **Loading state**: Should see "Checking session..." with spinner while auth check is in progress (no form flicker)
- [ ] **Expired token**: User with expired/invalid token visits `/login` → token cleared, login form shown
- [ ] **After successful login**: Complete login form → should redirect to `next` parameter or default page based on user role
- [ ] **No token**: User with no token visits `/login` → should see form immediately (minimal delay)
- [ ] **Admin with next param**: Admin visits `/login?next=/account` → should redirect to `/account` (respects next over role-based default)

### Security Notes
- `getNextUrl()` validates that redirect URLs are:
  - Same-origin (start with `/`)
  - Not protocol-relative URLs (`//example.com`)
  - Not javascript: or data: URLs
- Invalid `next` parameters fall back to safe defaults (`/dashboard` or `/admin`)

### Files Modified
- `web/src/lib/api.ts` - Added `getCurrentUser()` function
- `web/src/lib/utils.ts` - Added `getNextUrl()` helper for safe redirects
- `web/src/app/login/page.tsx` - Added auth check on mount with loading state and redirect logic

