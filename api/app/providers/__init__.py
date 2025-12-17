from app.core.config import Settings
from app.providers.marketcheck import MarketCheckProvider
from app.providers.copart_public import CopartPublicProvider
from app.providers.web_crawl import WebCrawlOnDemandProvider
from app.providers.internal_catalog import InternalCatalogProvider


def _provider_map(settings: Settings, config_map: dict | None = None):
    config_map = config_map or {}
    return {
        "marketcheck": MarketCheckProvider(settings),
        "copart_public": CopartPublicProvider(),
        "web_crawl_on_demand": WebCrawlOnDemandProvider(settings, config=config_map.get("web_crawl_on_demand")),
        "internal_catalog": InternalCatalogProvider(),
    }


def get_active_providers(settings: Settings, allowed_keys: list[str] | None = None, config_map: dict | None = None):
    provider_dict = _provider_map(settings, config_map=config_map)
    if allowed_keys is not None:
        # ONLY return providers explicitly in allowed_keys (respects admin DB settings)
        # Do NOT add extras - admin settings take precedence over config
        ordered = []
        for key in allowed_keys:
            p = provider_dict.get(key)
            if p and p.enabled:
                ordered.append(p)
        return ordered
    # Fallback: if no allowed_keys specified, return all config-enabled providers
    return [p for p in provider_dict.values() if p.enabled]


def get_provider_sources(settings: Settings, config_map: dict | None = None):
    provider_dict = _provider_map(settings, config_map=config_map)
    return list(provider_dict.values())
