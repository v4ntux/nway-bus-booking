from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://nway:nway@localhost:5432/nway"
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 14
    BOOKING_HOLD_MINUTES: int = 10
    OFFLINE_BOOKING_DEADLINE_MINUTES: int = 120
    LARGE_BOOKING_THRESHOLD: int = 4
    DEFAULT_CURRENCY: str = "UZS"
    SEED_ADMIN_EMAIL: str = "admin@demo.local"
    SEED_ADMIN_PASSWORD: str = "changeme"
    SEED_SUPERADMIN_EMAIL: str = "superadmin@demo.local"
    SEED_SUPERADMIN_PASSWORD: str = "changeme"
    SEED_ADMIN_PHONE: str = "+998901111111"
    SEED_PASSENGER_PHONE: str = "+998901234567"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    OTP_EXPIRE_MINUTES: int = 5
    OTP_CODE_LENGTH: int = 6
    LOG_LEVEL: str = "INFO"
    JWT_ALGORITHM: str = "HS256"

    # Telegram Mini App + bot (optional; bot CLI requires both)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBAPP_URL: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        """Normalize Railway/Heroku postgres URLs for async SQLAlchemy."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
