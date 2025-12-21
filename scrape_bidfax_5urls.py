"""
BidFax Multi-URL Scraper - Scrape 5 Different Vehicle Pages

This script will:
1. Scrape 5 different BidFax URLs
2. Use your cookies for Cloudflare bypass
3. Parse auction listings from each page
4. Save results to JSON file
"""

import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

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

# 5 URLs to scrape
URLS_TO_SCRAPE = [
    {
        "url": "https://en.bidfax.info/toyota/4runner/",
        "make": "Toyota",
        "model": "4Runner"
    },
    {
        "url": "https://en.bidfax.info/ford/mustang/",
        "make": "Ford",
        "model": "Mustang"
    },
    {
        "url": "https://en.bidfax.info/chevrolet/silverado-1500/",
        "make": "Chevrolet",
        "model": "Silverado 1500"
    },
    {
        "url": "https://en.bidfax.info/honda/civic/",
        "make": "Honda",
        "model": "Civic"
    },
    {
        "url": "https://en.bidfax.info/nissan/altima/",
        "make": "Nissan",
        "model": "Altima"
    }
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


def parse_bidfax_listings(html, url):
    """Parse BidFax HTML to extract auction listings."""
    soup = BeautifulSoup(html, 'html.parser')

    listings = []

    # Find all listing cards (div.thumbnail.offer)
    cards = soup.find_all('div', class_='thumbnail offer')

    for card in cards:
        try:
            listing = {
                'source_url': url,
                'scraped_at': datetime.now().isoformat()
            }

            # VIN - from h2 title (regex extraction)
            h2 = card.find('h2')
            if h2:
                title_text = h2.get_text()
                import re
                vin_match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', title_text)
                if vin_match:
                    listing['vin'] = vin_match.group(0)

            # Price - span.prices
            price_span = card.find('span', class_='prices')
            if price_span:
                price_text = price_span.get_text().strip()
                # Extract number from "$25,000" format
                price_match = re.search(r'\$?([\d,]+)', price_text)
                if price_match:
                    listing['sold_price'] = int(price_match.group(1).replace(',', ''))

            # Lot ID - "Lot number:" label + span.blackfont
            lot_label = card.find(string=re.compile(r'Lot number:', re.IGNORECASE))
            if lot_label:
                lot_span = lot_label.find_next('span', class_='blackfont')
                if lot_span:
                    listing['lot_id'] = lot_span.get_text().strip()

            # Auction Source - span.copart or span.iaai
            copart = card.find('span', class_='copart')
            iaai = card.find('span', class_='iaai')
            if copart:
                listing['auction_source'] = 'copart'
            elif iaai:
                listing['auction_source'] = 'iaai'

            # Sale Status - img[alt] (Sold/On approval/No sale)
            status_img = card.find('img', alt=True)
            if status_img:
                alt_text = status_img['alt'].lower()
                if 'sold' in alt_text:
                    listing['sale_status'] = 'sold'
                elif 'approval' in alt_text:
                    listing['sale_status'] = 'pending'
                elif 'no sale' in alt_text:
                    listing['sale_status'] = 'not_sold'

            # Date - "Date of sale:" + DD.MM.YYYY
            date_label = card.find(string=re.compile(r'Date of sale:', re.IGNORECASE))
            if date_label:
                date_span = date_label.find_next('span', class_='blackfont')
                if date_span:
                    listing['sale_date'] = date_span.get_text().strip()

            # Odometer - text with "miles"
            odometer_text = card.find(string=re.compile(r'(\d+)\s*miles', re.IGNORECASE))
            if odometer_text:
                odometer_match = re.search(r'(\d+)\s*miles', odometer_text, re.IGNORECASE)
                if odometer_match:
                    listing['odometer'] = int(odometer_match.group(1))

            # Damage - "Damage:" label + span.blackfont
            damage_label = card.find(string=re.compile(r'Damage:', re.IGNORECASE))
            if damage_label:
                damage_span = damage_label.find_next('span', class_='blackfont')
                if damage_span:
                    listing['damage'] = damage_span.get_text().strip()

            # Condition - "Condition:" label + span.blackfont
            condition_label = card.find(string=re.compile(r'Condition:', re.IGNORECASE))
            if condition_label:
                condition_span = condition_label.find_next('span', class_='blackfont')
                if condition_span:
                    listing['condition'] = condition_span.get_text().strip()

            # Location
            location_label = card.find(string=re.compile(r'Location:', re.IGNORECASE))
            if location_label:
                location_span = location_label.find_next('span', class_='blackfont')
                if location_span:
                    listing['location'] = location_span.get_text().strip()

            # Only add if we got at least some data
            if len(listing) > 2:  # More than just source_url and scraped_at
                listings.append(listing)

        except Exception as e:
            print(f"   Error parsing card: {e}")
            continue

    return listings


print("=" * 80)
print("BIDFAX MULTI-URL SCRAPER")
print("=" * 80)
print()
print(f"Target URLs: {len(URLS_TO_SCRAPE)}")
print(f"Cookies: {len(COOKIES)} characters")
print()

all_results = []
total_listings = 0

with sync_playwright() as p:
    # Launch browser (headless for speed)
    print("Launching browser...")
    browser = p.chromium.launch(
        headless=False,  # Set to True for faster scraping
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
    )

    # Create context with cookies
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
    )

    # Inject cookies once
    cookie_list = parse_cookies(URLS_TO_SCRAPE[0]['url'], COOKIES)
    context.add_cookies(cookie_list)
    print(f"Injected {len(cookie_list)} cookies")
    print()

    # Scrape each URL
    for idx, target in enumerate(URLS_TO_SCRAPE, 1):
        print(f"[{idx}/{len(URLS_TO_SCRAPE)}] Scraping: {target['make']} {target['model']}")
        print(f"    URL: {target['url']}")

        try:
            # Create new page
            page = context.new_page()

            # Navigate
            start_time = time.time()
            response = page.goto(target['url'], wait_until='domcontentloaded', timeout=30000)
            load_time = time.time() - start_time

            print(f"    Status: {response.status} | Load time: {load_time:.2f}s")

            # Get HTML
            html = page.content()
            print(f"    HTML size: {len(html):,} characters")

            # Parse listings
            listings = parse_bidfax_listings(html, target['url'])
            print(f"    Listings found: {len(listings)}")

            # Add to results
            result = {
                'url': target['url'],
                'make': target['make'],
                'model': target['model'],
                'status': response.status,
                'load_time': load_time,
                'html_size': len(html),
                'listings_count': len(listings),
                'listings': listings,
                'scraped_at': datetime.now().isoformat()
            }
            all_results.append(result)
            total_listings += len(listings)

            # Show first listing as sample
            if listings:
                first = listings[0]
                print(f"    Sample: VIN={first.get('vin', 'N/A')[:10]}... | "
                      f"Price=${first.get('sold_price', 0):,} | "
                      f"Lot={first.get('lot_id', 'N/A')}")

            page.close()
            print()

            # Small delay between requests
            time.sleep(2)

        except Exception as e:
            print(f"    ERROR: {e}")
            print()
            continue

    browser.close()

# Save results to JSON
output_file = f"bidfax_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print("=" * 80)
print("SCRAPING COMPLETE")
print("=" * 80)
print()
print(f"URLs scraped: {len(all_results)}/{len(URLS_TO_SCRAPE)}")
print(f"Total listings: {total_listings}")
print(f"Results saved to: {output_file}")
print()

# Show summary table
print("Summary:")
print("-" * 80)
for result in all_results:
    print(f"{result['make']:12} {result['model']:20} | "
          f"{result['listings_count']:3} listings | "
          f"Status: {result['status']} | "
          f"{result['load_time']:.1f}s")
print("-" * 80)
print()
print(f"Total listings scraped: {total_listings}")
print()
