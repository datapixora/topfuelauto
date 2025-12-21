"""
Test Production BidFax Scraper with Visual Browser + 2Captcha

This uses your existing production code:
- BidfaxHtmlProvider (parsing logic)
- BrowserFetcher (with 2Captcha)
- Proxy pool integration
- Visual browser mode
"""

import sys
import os
from pathlib import Path

# Add API directory to path
sys.path.insert(0, str(Path(__file__).parent / "api"))

# Set environment variables for visual mode
os.environ['TWOCAPTCHA_API_KEY'] = 'eef84e96e2d50be92a8453cd4c157dc0'
os.environ['CAPTCHA_SOLVER_ENABLED'] = 'true'
os.environ['CLOUDFLARE_WAIT_TIMEOUT'] = '60'

from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider
from app.services.sold_results.fetchers.browser_fetcher import BrowserFetcher
from app.database import SessionLocal
from app.services import proxy_service
import json
from datetime import datetime

# Your cookies
COOKIES = (
    "_ga=GA1.2.616046868.1766239869; "
    "_gid=GA1.2.1253003288.1766239869; "
    "cf_clearance=xZR62v8ViJT8QQrWpDiL9QcoVOoUtRSJZK0O1eY8.C4-1766299996-1.2.1.1-"
    "bztv7RAfEk96V1pMTe_eIPyJZ_bAiCwXdprAhxjdlebhr3vWvj3s53pdnZTKo4kpnp7yvI82cvog8Mm4h934edopKjFrmhLT5VcDafPH9Y70KuzmAB3ZtG6gOjo.oXcE8WlCv6JyIR3WzfuuCZqj.JyaM9O3mqmCz9rRWnxrnK7Y3iciSsb_2_RigJNtb9LbqSm.YO95YaKuHapb.Ioh_5kRlNtLuxxUrq6.cAl0TjQ; "
    "PHPSESSID=c46059d7c7060f9b481564c0449664a3"
)

# URLs to scrape
URLS = [
    {"url": "https://en.bidfax.info/toyota/4runner/", "make": "Toyota", "model": "4Runner"},
    {"url": "https://en.bidfax.info/ford/mustang/", "make": "Ford", "model": "Mustang"},
    {"url": "https://en.bidfax.info/chevrolet/silverado-1500/", "make": "Chevrolet", "model": "Silverado"},
    {"url": "https://en.bidfax.info/honda/civic/", "make": "Honda", "model": "Civic"},
    {"url": "https://en.bidfax.info/nissan/altima/", "make": "Nissan", "model": "Altima"},
]


class VisualBidfaxProvider(BidfaxHtmlProvider):
    """Override to use visual browser mode."""

    def __init__(self, rate_limit_per_minute: int = 30):
        super().__init__(rate_limit_per_minute)
        # Replace with visual browser
        self.browser_fetcher = BrowserFetcher(
            headless=False,  # VISUAL MODE
            timeout_ms=60000,  # 60 seconds for CAPTCHA solving
            solve_captcha=True  # Enable 2Captcha
        )


print("=" * 80)
print("PRODUCTION BIDFAX SCRAPER TEST")
print("=" * 80)
print()
print("Features:")
print("  - Visual browser mode (headless=False)")
print("  - 2Captcha integration (auto-solve challenges)")
print("  - Cookie support (Cloudflare bypass)")
print("  - Your existing parsing logic")
print("  - Optional proxy pool support")
print()

# Ask about proxy
use_proxy = input("Use proxy from your proxy pool? (y/n): ").lower() == 'y'
proxy_url = None
proxy_id = None

if use_proxy:
    db = SessionLocal()
    try:
        # Get first healthy proxy
        proxies = proxy_service.list_proxies(db, enabled_only=True, healthy_only=True)
        if proxies:
            proxy = proxies[0]
            proxy_id = proxy.id
            proxy_url = proxy_service.build_proxy_url(proxy)
            print(f"\nUsing proxy: {proxy.host}:{proxy.port}")
        else:
            print("\nNo healthy proxies found, proceeding without proxy")
    finally:
        db.close()

print(f"\nScraping {len(URLS)} URLs...")
print("Watch the browser window!\n")

# Initialize provider
provider = VisualBidfaxProvider()

all_results = []

for idx, target in enumerate(URLS, 1):
    print(f"[{idx}/{len(URLS)}] {target['make']} {target['model']}")
    print(f"    URL: {target['url']}")

    try:
        # Fetch HTML
        fetch_result = provider.fetch_list_page(
            url=target['url'],
            proxy_url=proxy_url,
            fetch_mode="browser",
            cookies=COOKIES
        )

        print(f"    Status: {fetch_result.status_code}")
        print(f"    Latency: {fetch_result.latency_ms}ms")
        print(f"    HTML size: {len(fetch_result.html):,} chars")
        print(f"    Cloudflare bypassed: {fetch_result.cloudflare_bypassed}")

        if fetch_result.error:
            print(f"    ERROR: {fetch_result.error}")
            continue

        # Parse listings
        listings = provider.parse_list_page(fetch_result.html, target['url'])
        print(f"    Listings found: {len(listings)}")

        if listings:
            first = listings[0]
            print(f"    Sample: VIN={first.get('vin', 'N/A')[:10]}... | "
                  f"Price=${first.get('sold_price', 0):,} | "
                  f"Lot={first.get('lot_id', 'N/A')}")

        result = {
            'url': target['url'],
            'make': target['make'],
            'model': target['model'],
            'status': fetch_result.status_code,
            'latency_ms': fetch_result.latency_ms,
            'cloudflare_bypassed': fetch_result.cloudflare_bypassed,
            'listings_count': len(listings),
            'listings': listings,
            'scraped_at': datetime.now().isoformat()
        }
        all_results.append(result)

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()

# Save results
output_file = f"production_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2)

print("=" * 80)
print("SCRAPING COMPLETE")
print("=" * 80)
print()
print(f"URLs scraped: {len(all_results)}/{len(URLS)}")
print(f"Total listings: {sum(r['listings_count'] for r in all_results)}")
print(f"Results saved to: {output_file}")
print()

# Summary
print("Summary:")
print("-" * 80)
for r in all_results:
    cloudflare = "BYPASSED" if r['cloudflare_bypassed'] else "BLOCKED"
    print(f"{r['make']:12} {r['model']:15} | {r['listings_count']:3} listings | "
          f"CF: {cloudflare:8} | {r['latency_ms']}ms")
print("-" * 80)
