# Sold Results Strategy System - Design Document

## Current State Analysis

### Frontend (`web/src/app/admin/data/sold-results/page.tsx`)
- ✅ Has Test Parse UI with fetch mode selection (http/browser)
- ✅ Has Create Crawl Job form with fields: url, pages, fetch_mode, schedule, proxy
- ✅ Sends `strategy_id` to backend (line 101) but defaults to "default"
- ✅ Has proxy dropdown loaded from `/api/v1/admin/proxies/options`
- ❌ Strategy dropdown shows hardcoded options (not loaded from API)
- ❌ No "Watch browser" checkbox
- ❌ No batch_size, rpm, concurrency fields in schema (only in UI state)

### Backend (`api/app/routers/admin_auction.py`)
- ✅ Has endpoints: POST /jobs, GET /tracking, POST /test-parse, POST /retry
- ❌ No GET /strategies endpoint
- ❌ Job creation ignores strategy_id (doesn't pass to worker)
- ❌ No support for batch_size, rpm, concurrency in schema

### Worker (`api/app/workers/auction.py`)
- ✅ `enqueue_bidfax_crawl` creates AuctionTracking rows
- ✅ `fetch_and_parse_tracking` processes one URL with BidfaxHtmlProvider
- ❌ No strategy abstraction - hardcoded to use BidfaxHtmlProvider
- ❌ No support for different parsing strategies
- ❌ No watch mode (always headless)

### Provider (`api/app/services/sold_results/providers/bidfax.py`)
- ✅ Has BidfaxHtmlProvider with HTTP and browser fetch modes
- ✅ BrowserFetcher supports cookies and 2Captcha
- ❌ BrowserFetcher always uses headless=True (line 31)
- ❌ No trace/video/screenshot artifacts captured

---

## Proposed Design

### 1. Strategy Registry (Backend)

**File**: `api/app/services/sold_results/strategy_registry.py` (NEW)

```python
from dataclasses import dataclass
from typing import List, Optional, Protocol

@dataclass
class StrategyMetadata:
    id: str
    label: str
    description: str
    supports_fetch_modes: List[str]  # ["http", "browser"]
    supports_watch_mode: bool
    default_fetch_mode: str
    notes: Optional[str] = None

class ScrapeStrategy(Protocol):
    """Protocol for scraping strategies."""
    def fetch_and_parse(self, url: str, config: dict) -> dict:
        ...

# Global registry
STRATEGIES: dict[str, StrategyMetadata] = {
    "bidfax_default": StrategyMetadata(
        id="bidfax_default",
        label="Bidfax HTTP (Fast)",
        description="HTTP fetch with BeautifulSoup parsing",
        supports_fetch_modes=["http"],
        supports_watch_mode=False,
        default_fetch_mode="http",
        notes="Fastest option, may be blocked by Cloudflare"
    ),
    "bidfax_browser": StrategyMetadata(
        id="bidfax_browser",
        label="Bidfax Browser (Robust)",
        description="Playwright browser with cookie/2Captcha support",
        supports_fetch_modes=["browser"],
        supports_watch_mode=True,
        default_fetch_mode="browser",
        notes="Slower but bypasses Cloudflare. Supports watch mode locally."
    ),
}

def get_strategy_metadata(strategy_id: str) -> Optional[StrategyMetadata]:
    return STRATEGIES.get(strategy_id)

def list_strategies() -> List[StrategyMetadata]:
    return list(STRATEGIES.values())
```

### 2. New API Endpoint

**File**: `api/app/routers/admin_auction.py` (MODIFY)

Add:
```python
@router.get("/strategies", response_model=List[schemas.StrategyResponse])
def list_strategies(admin: User = Depends(get_current_admin)):
    """
    List available scraping strategies.

    Returns strategy metadata including:
    - id: Strategy identifier
    - label: Human-readable name
    - supports_fetch_modes: Allowed fetch modes
    - supports_watch_mode: Whether visual browser is available
    """
    from app.services.sold_results.strategy_registry import list_strategies
    return list_strategies()
```

### 3. Schema Updates

**File**: `api/app/schemas/auction.py` (MODIFY)

Add:
```python
class StrategyResponse(BaseModel):
    id: str
    label: str
    description: str
    supports_fetch_modes: List[str]
    supports_watch_mode: bool
    default_fetch_mode: str
    notes: Optional[str] = None

class BidfaxJobCreate(BaseModel):
    target_url: str
    pages: int = 1
    make: Optional[str] = None
    model: Optional[str] = None
    schedule_enabled: bool = False
    schedule_interval_minutes: Optional[int] = 60
    proxy_id: Optional[int] = None
    fetch_mode: str = "http"
    cookies: Optional[str] = None
    strategy_id: str = "bidfax_default"  # ADD THIS
    watch_mode: bool = False  # ADD THIS (local only)
    use_2captcha: bool = False  # ADD THIS
```

### 4. Watch Mode Support

**Location**: `api/app/services/sold_results/providers/bidfax.py`

Current:
```python
self.browser_fetcher = BrowserFetcher(headless=True, timeout_ms=30000)
```

Proposed:
```python
def __init__(self, rate_limit_per_minute: int = 30, headless: bool = True,
             watch_mode: bool = False, use_2captcha: bool = False):
    self.http_fetcher = HttpFetcher(rate_limit_per_minute)
    self.browser_fetcher = BrowserFetcher(
        headless=not watch_mode if watch_mode else headless,
        timeout_ms=60000 if use_2captcha else 30000,
        solve_captcha=use_2captcha,
        slow_mo=150 if watch_mode else 0
    )
```

### 5. Frontend Strategy Loading

**File**: `web/src/app/admin/data/sold-results/page.tsx` (MODIFY)

Add state:
```typescript
const [strategies, setStrategies] = useState<Strategy[]>([]);
const [watchMode, setWatchMode] = useState(false);
const [use2Captcha, setUse2Captcha] = useState(false);
```

Load strategies:
```typescript
useEffect(() => {
  const loadStrategies = async () => {
    const data = await getStrategies(); // New API call
    setStrategies(data);
  };
  void loadStrategies();
}, []);
```

Update UI to show strategy dropdown populated from API.

### 6. Data Flow

```
UI: User selects strategy "bidfax_browser" + watch_mode=true
  ↓
API: POST /api/v1/admin/data-engine/bidfax/jobs
  ↓
Worker: enqueue_bidfax_crawl(strategy_id="bidfax_browser", watch_mode=true)
  ↓
Creates AuctionTracking rows with stats.strategy_id, stats.watch_mode
  ↓
Worker: fetch_and_parse_tracking reads stats, instantiates BidfaxHtmlProvider(watch_mode=True)
  ↓
BrowserFetcher launches Playwright with headless=False, slow_mo=150
  ↓
User can WATCH browser scraping in real-time (local dev only)
```

---

## Implementation Notes

### Watch Mode Safety
- Only enable headless=False when:
  - `watch_mode=True` AND
  - Running in local dev (check env: `APP_ENV != "production"`)
- In production: always run headless, log warning if watch_mode requested

### Artifacts (for production observability)
- When running browser mode in production:
  - Enable Playwright tracing: `context.tracing.start()`
  - Save trace.zip to: `api/artifacts/traces/{tracking_id}/`
  - Add `trace_url` field to AuctionTracking
  - UI: Show "Download trace" link in tracking detail

### 2Captcha Integration
- Strategy config includes `use_2captcha` boolean
- BrowserFetcher already supports it (implemented in previous session)
- Just need to wire the parameter through from UI → API → Worker → Provider

---

## Files to Create/Modify (Step 1)

**CREATE**:
- `api/app/services/sold_results/strategy_registry.py` - Strategy metadata and registry

**MODIFY**:
- `api/app/schemas/auction.py` - Add StrategyResponse, update BidfaxJobCreate
- `api/app/routers/admin_auction.py` - Add GET /strategies endpoint
- `web/src/lib/api.ts` - Add getStrategies() function
- `web/src/lib/types.ts` - Add Strategy type

**NO CHANGES YET** (will do in later steps):
- Worker logic
- Provider instantiation
- UI dropdowns

---

## Testing Plan (Step 1)

After creating strategy registry + API:

1. **Backend**: Run API server
   ```bash
   cd api
   uvicorn app.main:app --reload
   ```

2. **Test endpoint**:
   ```bash
   curl http://localhost:8000/api/v1/admin/data-engine/bidfax/strategies \
     -H "Authorization: Bearer <admin_token>"
   ```

   Expected: JSON array with 2 strategies (bidfax_default, bidfax_browser)

3. **UI**: Visit http://localhost:3000/admin/data/sold-results
   - Should still load (no breaking changes)
   - Strategy dropdown still shows hardcoded options (will fix in Step 3)

---

**STATUS**: Design complete. No code changes yet.
**NEXT**: Wait for OK to proceed to Step 2 (implement strategy registry + API).
