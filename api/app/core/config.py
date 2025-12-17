from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TopFuel Auto API"
    secret_key: str = Field("change-me", alias="JWT_SECRET")
    legacy_secret_key: str | None = Field(default=None, alias="SECRET_KEY")
    app_secret_key: str | None = Field(default=None, alias="APP_SECRET")
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    token_expires_seconds: int | None = None

    database_url: str = Field(
        "postgresql+psycopg2://topfuel:topfuel@localhost:5432/topfuel",
        alias="DATABASE_URL",
    )
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field("redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")

    marketcheck_api_key: str | None = Field(default=None, alias="MARKETCHECK_API_KEY")
    marketcheck_api_secret: str | None = Field(default=None, alias="MARKETCHECK_API_SECRET")
    marketcheck_api_base: str = Field("https://mc-api.marketcheck.com/v2", alias="MARKETCHECK_API_BASE")
    marketcheck_enabled: bool = Field(default=True, alias="MARKETCHECK_ENABLED")

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://topfuelauto.com",
            "https://www.topfuelauto.com",
        ],
        alias="ALLOWED_ORIGINS",
    )
    nhtsa_api_base: str = Field("https://vpic.nhtsa.dot.gov/api/vehicles", alias="NHTSA_API_BASE")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    public_web_url: str = Field("https://topfuelauto.com", alias="PUBLIC_WEB_URL")

    # On-demand crawl search
    crawl_search_allowlist: List[str] = Field(default_factory=list, alias="CRAWL_SEARCH_ALLOWLIST")
    crawl_search_rate_per_minute: int = Field(30, alias="CRAWL_SEARCH_RATE_PER_MINUTE")
    crawl_search_concurrency: int = Field(2, alias="CRAWL_SEARCH_CONCURRENCY")
    crawl_search_max_sources: int = Field(2, alias="CRAWL_SEARCH_MAX_SOURCES")
    crawl_search_min_results: int = Field(3, alias="CRAWL_SEARCH_MIN_RESULTS")

    # Release tracking
    git_sha: str | None = Field(default=None, alias="GIT_SHA")
    build_time: str | None = Field(default=None, alias="BUILD_TIME")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("crawl_search_allowlist", mode="before")
    @classmethod
    def split_crawl_allowlist(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def marketcheck_active(self) -> bool:
        return bool(
            self.marketcheck_enabled
            and self.marketcheck_api_key
            and self.marketcheck_api_secret
        )

    @property
    def jwt_secret(self) -> str:
        if self.secret_key and self.secret_key != "change-me":
            return self.secret_key
        if self.legacy_secret_key:
            return self.legacy_secret_key
        if self.app_secret_key:
            return self.app_secret_key
        return self.secret_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
