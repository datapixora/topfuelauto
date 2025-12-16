from app.core.config import Settings
from app.providers.marketcheck import MarketCheckProvider
from app.providers.copart_public import CopartPublicProvider
from app.providers.web_crawl import WebCrawlOnDemandProvider


def _provider_map(settings: Settings, config_map: dict | None = None):
    config_map = config_map or {}
    return {
        "marketcheck": MarketCheckProvider(settings),
        "copart_public": CopartPublicProvider(),
        "web_crawl_on_demand": WebCrawlOnDemandProvider(settings, config=config_map.get("web_crawl_on_demand")),
    }


def get_active_providers(settings: Settings, allowed_keys: list[str] | None = None, config_map: dict | None = None):
    provider_dict = _provider_map(settings, config_map=config_map)
    if allowed_keys:
        ordered = []
        for key in allowed_keys:
            p = provider_dict.get(key)
            if p and p.enabled:
                ordered.append(p)
        # include any additional enabled providers not in allowed_keys
        extras = [p for k, p in provider_dict.items() if (not allowed_keys or k not in allowed_keys) and p.enabled]
        return ordered + extras
    return [p for p in provider_dict.values() if p.enabled]


def get_provider_sources(settings: Settings, config_map: dict | None = None):
    provider_dict = _provider_map(settings, config_map=config_map)
    return list(provider_dict.values())
