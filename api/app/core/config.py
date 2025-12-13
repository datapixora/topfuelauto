from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TopFuel Auto API"
    secret_key: str = Field("change-me", alias="JWT_SECRET")
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    database_url: str = Field(
        "postgresql+psycopg2://topfuel:topfuel@localhost:5432/topfuel",
        alias="DATABASE_URL",
    )
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field("redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://app.topfuelauto.com",
        ],
        alias="CORS_ORIGINS",
    )
    nhtsa_api_base: str = Field("https://vpic.nhtsa.dot.gov/api/vehicles", alias="NHTSA_API_BASE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
