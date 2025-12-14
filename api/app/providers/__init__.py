from app.core.config import Settings
from app.providers.marketcheck import MarketCheckProvider


def get_active_providers(settings: Settings):
    providers = [MarketCheckProvider(settings)]
    return [p for p in providers if p.enabled]


def get_provider_sources(settings: Settings):
    providers = [MarketCheckProvider(settings)]
    return providers
