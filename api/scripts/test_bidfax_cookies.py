"""
Test BidFax scraping with Cloudflare bypass cookies.

This script demonstrates how to use cookies to bypass Cloudflare protection
on BidFax and successfully scrape auction data.

Usage:
    python api/scripts/test_bidfax_cookies.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.sold_results.fetchers.browser_fetcher import BrowserFetcher
from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider


def test_bidfax_with_cookies():
    """Test BidFax scraping with provided Cloudflare cookies."""

    # Your BidFax cookies (from the browser)
    BIDFAX_COOKIES = (
        "_ga=GA1.2.616046868.1766239869; "
        "_gid=GA1.2.1253003288.1766239869; "
        "cf_clearance=xZR62v8ViJT8QQrWpDiL9QcoVOoUtRSJZK0O1eY8.C4-1766299996-1.2.1.1-"
        "bztv7RAfEk96V1pMTe_eIPyJZ_bAiCwXdprAhxjdlebhr3vWvj3s53pdnZTKo4kpnp7yvI82cvog8Mm4h934edopKjFrmhLT5VcDafPH9Y70KuzmAB3ZtG6gOjo.oXcE8WlCv6JyIR3WzfuuCZqj.JyaM9O3mqmCz9rRWnxrnK7Y3iciSsb_2_RigJNtb9LbqSm.YO95YaKuHapb.Ioh_5kRlNtLuxxUrq6.cAl0TjQ; "
        "_gat_UA-130669464-1=1; "
        "_gat_UA-130669464-2=1; "
        "__eoi=ID=b9ebbd2dbd5571e8:T=1766239868:RT=1766299997:S=AA-AfjaK3_HZyzTkQTPrESY9FAgs; "
        "PHPSESSID=c46059d7c7060f9b481564c0449664a3; "
        "_ga_JHF17MVRXG=GS2.2.s1766299998$o4$g1$t1766300004$j54$l0$h0; "
        "_ga_X74XC43NFG=GS2.2.s1766299998$o4$g1$t1766300004$j54$l0$h0"
    )

    # Test URL
    test_url = "https://en.bidfax.info/toyota/4runner/"

    print("=" * 80)
    print("BidFax Cookie Integration Test")
    print("=" * 80)
    print()
    print(f"Test URL: {test_url}")
    print(f"Cookies: {BIDFAX_COOKIES[:100]}..." if len(BIDFAX_COOKIES) > 100 else f"Cookies: {BIDFAX_COOKIES}")
    print()

    # Test 1: Browser fetch WITHOUT cookies (expect Cloudflare challenge)
    print("Test 1: Browser fetch WITHOUT cookies")
    print("-" * 80)
    try:
        fetcher = BrowserFetcher(headless=True, timeout_ms=30000)
        result_no_cookies = fetcher.fetch(test_url)

        print(f"Status Code: {result_no_cookies.status_code}")
        print(f"Latency: {result_no_cookies.latency_ms}ms")
        print(f"HTML Length: {len(result_no_cookies.html)}")
        print(f"Cloudflare Bypassed: {result_no_cookies.cloudflare_bypassed}")
        print(f"Error: {result_no_cookies.error or 'None'}")

        if not result_no_cookies.cloudflare_bypassed:
            print("❌ BLOCKED: Cloudflare challenge detected (as expected)")
        else:
            print("✅ SUCCESS: Page loaded without challenge")

        print()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()

    # Test 2: Browser fetch WITH cookies (expect bypass)
    print("Test 2: Browser fetch WITH cookies")
    print("-" * 80)
    try:
        fetcher = BrowserFetcher(headless=True, timeout_ms=30000)
        result_with_cookies = fetcher.fetch(test_url, cookies=BIDFAX_COOKIES)

        print(f"Status Code: {result_with_cookies.status_code}")
        print(f"Latency: {result_with_cookies.latency_ms}ms")
        print(f"HTML Length: {len(result_with_cookies.html)}")
        print(f"Cloudflare Bypassed: {result_with_cookies.cloudflare_bypassed}")
        print(f"Cookies Used: {bool(result_with_cookies.cookies_used)}")
        print(f"Error: {result_with_cookies.error or 'None'}")

        if result_with_cookies.cloudflare_bypassed:
            print("✅ SUCCESS: Cloudflare bypassed using cookies!")
        else:
            print("❌ BLOCKED: Cloudflare challenge still detected")

        print()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()

    # Test 3: Parse listings from bypassed page
    print("Test 3: Parse listings from bypassed page")
    print("-" * 80)
    try:
        provider = BidfaxHtmlProvider()
        result = provider.fetch_list_page(
            url=test_url,
            fetch_mode="browser",
            cookies=BIDFAX_COOKIES,
        )

        if result.cloudflare_bypassed and result.html:
            listings = provider.parse_list_page(result.html, test_url)
            print(f"Listings Found: {len(listings)}")

            if listings:
                print()
                print("First Listing:")
                first = listings[0]
                print(f"  VIN: {first.get('vin', 'N/A')}")
                print(f"  Price: ${first.get('sold_price', 0):,.0f}")
                print(f"  Lot: {first.get('lot_id', 'N/A')}")
                print(f"  Source: {first.get('auction_source', 'N/A')}")
                print(f"  Status: {first.get('sale_status', 'N/A')}")
                print(f"  Odometer: {first.get('odometer', 'N/A'):,} miles" if first.get('odometer') else "  Odometer: N/A")
                print()
                print("✅ SUCCESS: Listings parsed successfully!")
            else:
                print("❌ WARNING: No listings found (check selectors)")
        else:
            print("❌ BLOCKED: Could not fetch page content")

        print()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()

    print("=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_bidfax_with_cookies()
