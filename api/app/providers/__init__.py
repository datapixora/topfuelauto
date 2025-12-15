from app.core.config import Settings
from app.providers.marketcheck import MarketCheckProvider


def _provider_map(settings: Settings):
    return {
        "marketcheck": MarketCheckProvider(settings),
    }


def get_active_providers(settings: Settings, allowed_keys: list[str] | None = None):
    provider_dict = _provider_map(settings)
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


def get_provider_sources(settings: Settings):
    provider_dict = _provider_map(settings)
    return list(provider_dict.values())
