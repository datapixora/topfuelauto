"""
Strategy registry for sold results scraping.

Defines available scraping strategies and their capabilities.
Each strategy represents a different approach to fetching and parsing auction data.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StrategyMetadata:
    """Metadata describing a scraping strategy."""

    id: str
    """Unique strategy identifier"""

    label: str
    """Human-readable strategy name"""

    description: str
    """Strategy description for UI"""

    supports_fetch_modes: List[str]
    """Supported fetch modes: 'http', 'browser'"""

    supports_watch_mode: bool
    """Whether visual browser mode is available (local dev only)"""

    default_fetch_mode: str
    """Default fetch mode for this strategy"""

    supports_2captcha: bool = True
    """Whether strategy can use 2Captcha for challenge solving"""

    notes: Optional[str] = None
    """Additional notes or warnings"""


# Global strategy registry
STRATEGIES: dict[str, StrategyMetadata] = {
    "bidfax_default": StrategyMetadata(
        id="bidfax_default",
        label="Bidfax HTTP (Fast)",
        description="HTTP fetch with BeautifulSoup parsing",
        supports_fetch_modes=["http"],
        supports_watch_mode=False,
        default_fetch_mode="http",
        supports_2captcha=False,
        notes="Fastest option, may be blocked by Cloudflare. Use Browser mode if blocked."
    ),
    "bidfax_browser": StrategyMetadata(
        id="bidfax_browser",
        label="Bidfax Browser (Robust)",
        description="Playwright browser with cookie and 2Captcha support",
        supports_fetch_modes=["browser"],
        supports_watch_mode=True,
        default_fetch_mode="browser",
        supports_2captcha=True,
        notes="Slower but bypasses Cloudflare. Supports visual watch mode in local dev."
    ),
}


def get_strategy_metadata(strategy_id: str) -> Optional[StrategyMetadata]:
    """
    Get metadata for a specific strategy.

    Args:
        strategy_id: Strategy identifier (e.g., 'bidfax_default')

    Returns:
        StrategyMetadata if found, None otherwise
    """
    return STRATEGIES.get(strategy_id)


def list_strategies() -> List[StrategyMetadata]:
    """
    List all available strategies.

    Returns:
        List of all registered strategies
    """
    return list(STRATEGIES.values())


def validate_strategy_config(strategy_id: str, fetch_mode: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a strategy supports the requested fetch mode.

    Args:
        strategy_id: Strategy identifier
        fetch_mode: Requested fetch mode ('http' or 'browser')

    Returns:
        Tuple of (is_valid, error_message)
    """
    strategy = get_strategy_metadata(strategy_id)

    if not strategy:
        return False, f"Unknown strategy: {strategy_id}"

    if fetch_mode not in strategy.supports_fetch_modes:
        return False, f"Strategy '{strategy.label}' does not support fetch mode '{fetch_mode}'"

    return True, None
