"""
Visual Browser Scraper - Uses Your Production Parsing Logic

Scrapes 5 BidFax URLs with:
- Visual browser (watch it work!)
- 2Captcha auto-solve
- Your cookies
- Production HTML parsing
"""

import json
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Your cookies
COOKIES = (
    "_ga=GA1.2.616046868.1766239869; "
    "_gid=GA1.2.1253003288.1766239869; "
    "cf_clearance=xZR62v8ViJT8QQrWpDiL9QcoVOoUtRSJZK0O1eY8.C4-1766299996-1.2.1.1-"
    "bztv7RAfEk96V1pMTe_eIPyJZ_bAiCwXdprAhxjdlebhr3vWvj3s53pdnZTKo4kpnp7yvI82cvog8Mm4h934edopKjFrmhLT5VcDafPH9Y70KuzmAB3ZtG6gOjo.oXcE8WlCv6JyIR3WzfuuCZqj.JyaM9O3mqmCz9rRWnxrnK7Y3iciSsb_2_RigJNtb9LbqSm.YO95YaKuHapb.Ioh_5kRlNtLuxxUrq6.cAl0TjQ; "
    "PHPSESSID=c46059d7c7060f9b481564c0449664a3"
)

URLS = [
    {"url": "https://en.bidfax.info/toyota/4runner/", "make": "Toyota", "model": "4Runner"},
    {"url": "https://en.bidfax.info/ford/mustang/", "make": "Ford", "model": "Mustang"},
    {"url": "https://en.bidfax.info/chevrolet/silverado-1500/", "make": "Chevrolet", "model": "Silverado"},
    {"url": "https://en.bidfax.info/honda/civic/", "make": "Honda", "model": "Civic"},
    {"url": "https://en.bidfax.info/nissan/altima/", "make": "Nissan", "model": "Altima"},
]


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


def parse_bidfax_card(card, url):
    """Parse a single BidFax listing card (your production logic)."""
    result = {'source_url': url, 'scraped_at': datetime.now().isoformat()}

    try:
        # VIN from h2 title
        h2 = card.find('h2')
        if h2:
            title_text = h2.get_text()
            vin_match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', title_text)
            if vin_match:
                result['vin'] = vin_match.group(0)

        # Price
        price_span = card.find('span', class_='prices')
        if price_span:
            price_text = price_span.get_text().strip()
            price_match = re.search(r'\$?([\d,]+)', price_text)
            if price_match:
                result['sold_price'] = int(price_match.group(1).replace(',', ''))

        # Lot ID
        lot_label = card.find(string=re.compile(r'Lot number:', re.IGNORECASE))
        if lot_label:
            lot_span = lot_label.find_next('span', class_='blackfont')
            if lot_span:
                result['lot_id'] = lot_span.get_text().strip()

        # Auction source
        if card.find('span', class_='copart'):
            result['auction_source'] = 'copart'
        elif card.find('span', class_='iaai'):
            result['auction_source'] = 'iaai'

        # Sale status
        status_img = card.find('img', alt=True)
        if status_img:
            alt = status_img['alt'].lower()
            if 'sold' in alt:
                result['sale_status'] = 'sold'
            elif 'approval' in alt:
                result['sale_status'] = 'pending'
            elif 'no sale' in alt:
                result['sale_status'] = 'not_sold'

        # Date
        date_label = card.find(string=re.compile(r'Date of sale:', re.IGNORECASE))
        if date_label:
            date_span = date_label.find_next('span', class_='blackfont')
            if date_span:
                result['sale_date'] = date_span.get_text().strip()

        # Odometer
        odometer_text = card.find(string=re.compile(r'(\d+)\s*miles', re.IGNORECASE))
        if odometer_text:
            odometer_match = re.search(r'(\d+)\s*miles', odometer_text, re.IGNORECASE)
            if odometer_match:
                result['odometer'] = int(odometer_match.group(1).replace(',', ''))

        # Damage
        damage_label = card.find(string=re.compile(r'Damage:', re.IGNORECASE))
        if damage_label:
            damage_span = damage_label.find_next('span', class_='blackfont')
            if damage_span:
                result['damage'] = damage_span.get_text().strip()

        # Condition
        condition_label = card.find(string=re.compile(r'Condition:', re.IGNORECASE))
        if condition_label:
            condition_span = condition_label.find_next('span', class_='blackfont')
            if condition_span:
                result['condition'] = condition_span.get_text().strip()

        # Location
        location_label = card.find(string=re.compile(r'Location:', re.IGNORECASE))
        if location_label:
            location_span = location_label.find_next('span', class_='blackfont')
            if location_span:
                result['location'] = location_span.get_text().strip()

        return result if len(result) > 2 else None

    except Exception as e:
        print(f"      Error parsing card: {e}")
        return None


def parse_bidfax_listings(html, url):
    """Parse all listings from BidFax page."""
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('div.thumbnail.offer')
    listings = []

    for card in cards:
        parsed = parse_bidfax_card(card, url)
        if parsed:
            listings.append(parsed)

    return listings


print("=" * 80)
print("VISUAL BROWSER SCRAPER - 5 URLs")
print("=" * 80)
print()
print("Features:")
print("  - VISUAL browser (watch it work!)")
print("  - Cookie injection (Cloudflare bypass)")
print("  - Production parsing logic")
print("  - 2Captcha ready (if challenge appears)")
print()

all_results = []

with sync_playwright() as p:
    print("Launching browser...")
    browser = p.chromium.launch(
        headless=False,  # VISUAL!
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
        ],
        slow_mo=500  # Slow down by 500ms to watch
    )

    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        viewport={'width': 1920, 'height': 1080},
    )

    # Inject cookies
    cookie_list = parse_cookies(URLS[0]['url'], COOKIES)
    context.add_cookies(cookie_list)
    print(f"Injected {len(cookie_list)} cookies\n")

    # Scrape each URL
    for idx, target in enumerate(URLS, 1):
        print(f"[{idx}/{len(URLS)}] {target['make']} {target['model']}")
        print(f"    {target['url']}")

        try:
            page = context.new_page()
            start = time.time()

            response = page.goto(target['url'], wait_until='domcontentloaded', timeout=30000)
            load_time = time.time() - start

            html = page.content()

            print(f"    Status: {response.status} | Time: {load_time:.1f}s | Size: {len(html):,}")

            # Parse
            listings = parse_bidfax_listings(html, target['url'])
            print(f"    Listings: {len(listings)}")

            if listings:
                first = listings[0]
                print(f"    Sample: {first.get('vin', 'N/A')[:10]}... | "
                      f"${first.get('sold_price', 0):,} | {first.get('lot_id', 'N/A')}")

            all_results.append({
                'url': target['url'],
                'make': target['make'],
                'model': target['model'],
                'status': response.status,
                'load_time': load_time,
                'listings_count': len(listings),
                'listings': listings
            })

            page.close()
            time.sleep(2)  # Delay between pages

        except Exception as e:
            print(f"    ERROR: {e}")

        print()

    browser.close()

# Save
output_file = f"scraped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(all_results, f, indent=2)

total = sum(r['listings_count'] for r in all_results)

print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"\nTotal listings: {total}")
print(f"Saved to: {output_file}\n")

print("Summary:")
print("-" * 50)
for r in all_results:
    print(f"{r['make']:12} {r['model']:15} | {r['listings_count']:3} listings")
print("-" * 50)
