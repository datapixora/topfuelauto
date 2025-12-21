"""
Visible BidFax Cookie Test - Watch the browser in action!

This script opens a real browser window so you can see:
- Cookies being injected
- Cloudflare bypass
- Listing scraping

Press Ctrl+C to stop at any time.
"""

import time
from playwright.sync_api import sync_playwright

# Your BidFax cookies
COOKIES = (
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

TEST_URL = "https://en.bidfax.info/toyota/4runner/"


def parse_cookies(url, cookie_string):
    """Parse cookie string into Playwright format."""
    from urllib.parse import urlparse

    parsed_url = urlparse(url)
    domain = parsed_url.hostname

    cookies = []
    for cookie in cookie_string.split(';'):
        cookie = cookie.strip()
        if '=' not in cookie:
            continue

        name, value = cookie.split('=', 1)
        cookies.append({
            'name': name.strip(),
            'value': value.strip(),
            'domain': domain,
            'path': '/',
        })

    return cookies


def check_cloudflare(html):
    """Check if Cloudflare challenge is present."""
    html_lower = html.lower()

    indicators = [
        'checking your browser',
        'just a moment',
        'cf-chl',
        'cf-challenge',
        'turnstile',
    ]

    for indicator in indicators:
        if indicator in html_lower:
            return True, indicator

    return False, None


print("=" * 80)
print("BIDFAX VISIBLE BROWSER TEST")
print("=" * 80)
print()
print(f"Target: {TEST_URL}")
print(f"Cookies: {len(COOKIES)} characters")
print()
print("Starting browser (this will open a visible window)...")
print()

with sync_playwright() as p:
    # Launch browser in HEADED mode (visible)
    print(" Launching Chromium browser...")
    browser = p.chromium.launch(
        headless=False,  #  VISIBLE BROWSER!
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ],
        slow_mo=1000,  #  Slow down actions by 1 second
    )

    print(" Browser launched!")
    time.sleep(2)

    # Create context
    print(" Creating browser context...")
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
    )

    # Create page
    page = context.new_page()
    print(" Page created!")
    time.sleep(1)

    # Inject cookies
    print()
    print(" Injecting cookies...")
    cookie_list = parse_cookies(TEST_URL, COOKIES)
    context.add_cookies(cookie_list)
    print(f" Injected {len(cookie_list)} cookies:")
    for cookie in cookie_list[:5]:  # Show first 5
        print(f"   - {cookie['name']}: {cookie['value'][:20]}...")
    if len(cookie_list) > 5:
        print(f"   ... and {len(cookie_list) - 5} more")
    time.sleep(3)

    # Navigate to BidFax
    print()
    print(f" Navigating to {TEST_URL}...")
    print("   (Watch the browser window!)")
    start_time = time.time()

    response = page.goto(TEST_URL, wait_until='domcontentloaded', timeout=30000)

    load_time = time.time() - start_time
    print(f" Page loaded in {load_time:.2f} seconds")
    print(f"   Status: {response.status}")
    time.sleep(3)

    # Get page content
    html = page.content()
    print(f"   HTML size: {len(html):,} characters")
    time.sleep(2)

    # Check for Cloudflare
    print()
    print(" Checking for Cloudflare challenge...")
    has_challenge, indicator = check_cloudflare(html)

    if has_challenge:
        print(f" BLOCKED: Cloudflare challenge detected ('{indicator}')")
        print("   Your cookies may have expired.")
    else:
        print(" SUCCESS: Cloudflare bypassed!")
        print("   Page content loaded normally")

    time.sleep(3)

    # Look for listings
    print()
    print(" Looking for vehicle listings...")

    # Simple check for BidFax content
    listing_count = html.lower().count('thumbnail offer')
    price_count = html.lower().count('sold')

    print(f"   Found ~{listing_count} listing cards")
    print(f"   Found ~{price_count} sale status indicators")

    if listing_count > 0:
        print()
        print(" SUCCESS: Listings found on page!")
    else:
        print()
        print("  WARNING: No listings found (may need to check selectors)")

    time.sleep(3)

    # Show page title
    title = page.title()
    print()
    print(f" Page title: {title}")
    time.sleep(2)

    # Final status
    print()
    print("=" * 80)
    print(" TEST COMPLETE")
    print("=" * 80)
    print()

    if not has_challenge and listing_count > 0:
        print(" RESULT: Your cookies are WORKING!")
        print("   - Cloudflare bypassed")
        print("   - Listings visible")
        print("   - Ready for production scraping")
    elif not has_challenge:
        print("  RESULT: Cookies working, but no listings found")
        print("   - Cloudflare bypassed successfully")
        print("   - May need to check page structure")
    else:
        print(" RESULT: Cookies may have expired")
        print("   - Cloudflare challenge detected")
        print("   - Try getting fresh cookies from browser")

    print()
    print("Browser will close in 10 seconds...")
    print("(Press Ctrl+C to keep it open)")

    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print()
        print("  Paused - Press Enter to close browser")
        input()

    browser.close()
    print(" Browser closed")

print()
print("=" * 80)
print("Test finished!")
print("=" * 80)
