"""Admin API endpoints for site settings."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.services import settings_service
import logging

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin", "settings"])
logger = logging.getLogger(__name__)


class SettingUpdate(BaseModel):
    value: Optional[str]
    description: Optional[str] = None


@router.get("/bidfax-cookies")
def get_bidfax_cookies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get default Bidfax cookies for automatic injection."""
    cookies = settings_service.get_setting(db, "bidfax_cookies")
    return {
        "cookies": cookies,
        "has_cookies": bool(cookies),
        "info": "These cookies will be automatically injected in browser mode if no cookies are explicitly provided."
    }


@router.put("/bidfax-cookies")
def update_bidfax_cookies(
    payload: SettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update default Bidfax cookies.
    
    These cookies will be automatically injected when using browser mode,
    allowing bypass of Cloudflare challenges without manual input.
    
    To get cookies:
    1. Open https://en.bidfax.info in your browser
    2. Open DevTools (F12) -> Application -> Cookies
    3. Copy all cookies, especially cf_clearance
    4. Format: "cf_clearance=xxx; _ga=xxx; PHPSESSID=xxx"
    """
    setting = settings_service.set_setting(
        db,
        "bidfax_cookies",
        payload.value,
        payload.description or "Default cookies for Bidfax browser automation"
    )
    
    logger.info(f"Admin {admin.email} updated default Bidfax cookies")
    
    return {
        "success": True,
        "message": "Default cookies updated successfully",
        "has_cookies": bool(setting.value)
    }


@router.delete("/bidfax-cookies")
def delete_bidfax_cookies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Clear default Bidfax cookies."""
    deleted = settings_service.delete_setting(db, "bidfax_cookies")

    if deleted:
        logger.info(f"Admin {admin.email} deleted default Bidfax cookies")
        return {"success": True, "message": "Default cookies cleared"}

    return {"success": False, "message": "No cookies to delete"}


@router.post("/bidfax-cookies/refresh")
def refresh_bidfax_cookies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Automatically refresh Bidfax cookies by launching browser and solving Cloudflare.

    How it works:
    1. Launches headless Chromium browser
    2. Navigates to Bidfax homepage
    3. Waits for Cloudflare challenge to be solved (uses 2Captcha if configured)
    4. Extracts all cookies from browser session
    5. Saves cookies to database
    6. Returns cookies for verification

    This eliminates manual cookie extraction from DevTools!
    """
    from playwright.sync_api import sync_playwright
    import time

    try:
        logger.info(f"Admin {admin.email} initiated automatic cookie refresh")

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            # Create context
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
            )

            page = context.new_page()

            # Navigate to Bidfax
            logger.info("Navigating to Bidfax to obtain fresh cookies...")
            bidfax_url = "https://en.bidfax.info/"
            page.goto(bidfax_url, wait_until='domcontentloaded', timeout=30000)

            # Wait a bit for any redirects/challenges
            time.sleep(3)

            # Check if Cloudflare challenge is present
            html = page.content()
            has_challenge = any(indicator in html.lower() for indicator in [
                'checking your browser',
                'just a moment',
                'cf-chl',
                'turnstile',
            ])

            if has_challenge:
                logger.warning("Cloudflare challenge detected, waiting for bypass...")

                # Check if 2Captcha is configured
                import os
                if os.getenv('TWOCAPTCHA_API_KEY') and os.getenv('CAPTCHA_SOLVER_ENABLED', 'false').lower() == 'true':
                    logger.info("Attempting to solve Cloudflare challenge with 2Captcha...")
                    from app.services.sold_results.fetchers.browser_fetcher import BrowserFetcher

                    fetcher = BrowserFetcher(headless=True, solve_captcha=True)
                    solved = fetcher._solve_cloudflare_turnstile(page, bidfax_url)

                    if solved:
                        logger.info("Cloudflare challenge solved with 2Captcha")
                        time.sleep(2)
                    else:
                        browser.close()
                        return {
                            "success": False,
                            "error": "Failed to solve Cloudflare challenge automatically. Please configure 2Captcha or get cookies manually."
                        }
                else:
                    # Wait longer for manual bypass (in case running in headed mode locally)
                    logger.info("Waiting 10 seconds for Cloudflare to complete...")
                    time.sleep(10)
            else:
                logger.info("No Cloudflare challenge detected")

            # Extract cookies
            cookies = context.cookies()

            if not cookies:
                browser.close()
                return {
                    "success": False,
                    "error": "No cookies obtained from browser session"
                }

            # Format cookies as string
            cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            # Count important cookies
            important_cookies = ['cf_clearance', 'PHPSESSID', '_ga']
            found_cookies = [name for name in important_cookies if name in cookie_string]

            logger.info(f"Extracted {len(cookies)} cookies, including: {', '.join(found_cookies)}")

            # Save to database
            settings_service.set_setting(
                db,
                "bidfax_cookies",
                cookie_string,
                f"Auto-refreshed by {admin.email} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            browser.close()

            logger.info(f"Successfully refreshed Bidfax cookies for admin {admin.email}")

            return {
                "success": True,
                "message": f"Successfully refreshed {len(cookies)} cookies",
                "cookies_count": len(cookies),
                "important_cookies": found_cookies,
                "has_cf_clearance": "cf_clearance" in cookie_string,
                "preview": cookie_string[:100] + "..." if len(cookie_string) > 100 else cookie_string
            }

    except Exception as e:
        logger.error(f"Failed to refresh Bidfax cookies: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to refresh cookies: {str(e)}"
        }
