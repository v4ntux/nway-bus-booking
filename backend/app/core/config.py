import os
import ssl
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def _normalize_asyncpg_url(url: str) -> str:
    url = url.strip()
    # Railway's single-variable editor can preserve pasted .env quotes.
    if len(url) >= 2 and url[0] == url[-1] and url[0] in ("'", '"'):
        url = url[1:-1].strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _is_local_db(url: str) -> bool:
    host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://nway:nway@localhost:5432/nway"
    DATABASE_PRIVATE_URL: str = ""
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
    TELEGRAM_BOT_ENABLED: bool = False
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_SUPPORT: str = ""
    TELEGRAM_DEMO_MODE: bool = True
    TELEGRAM_BOOKING_CUTOFF_MINUTES: int = 30
    ALLOW_MOCK_PAYMENTS: bool = False

    def _raw_database_url(self) -> str:
        """Prefer the optional private override, then DATABASE_URL."""
        private = self.DATABASE_PRIVATE_URL.strip() or os.environ.get("DATABASE_PRIVATE_URL", "").strip()
        public = os.environ.get("DATABASE_URL", "").strip()
        if private:
            return private
        if public:
            return public
        return self.DATABASE_URL

    @property
    def database_url(self) -> str:
        return _normalize_asyncpg_url(self._raw_database_url())

    @property
    def database_connect_args(self) -> dict:
        """SSL for hosted Postgres (Railway public URL). Skip for localhost."""
        url = self.database_url
        if _is_local_db(url):
            return {}
        host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname or ""
        # Railway private network — no SSL needed
        if host.endswith(".railway.internal"):
            return {}
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}

    def ensure_database_configured(self) -> None:
        """Reject invalid settings before migrations, without exposing credentials."""
        on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME"))
        url = self.database_url
        has_private_override = bool(
            self.DATABASE_PRIVATE_URL.strip()
            or os.environ.get("DATABASE_PRIVATE_URL", "").strip()
        )
        variable = "DATABASE_PRIVATE_URL" if has_private_override else "DATABASE_URL"
        fix = (
            "In Railway, open the backend service → Variables and set DATABASE_URL "
            "to a reference to your Postgres service's DATABASE_URL "
            "(for a service named Postgres: ${{Postgres.DATABASE_URL}}). "
            "Remove or correct DATABASE_PRIVATE_URL if it overrides that value. "
            "Apply the changes and deploy."
        )
        if "${{" in url or "{{" in url:
            raise RuntimeError(f"{variable} contains an unresolved Railway reference. {fix}")
        try:
            parsed = make_url(url)
            valid = (
                parsed.drivername == "postgresql+asyncpg"
                and bool(parsed.host)
                and bool(parsed.database)
            )
        except (ArgumentError, ValueError):
            valid = False
        if not valid:
            raise RuntimeError(
                f"{variable} must be a complete PostgreSQL connection URL "
                f"starting with postgresql:// or postgresql+asyncpg://. {fix}"
            ) from None
        if on_railway and _is_local_db(url):
            raise RuntimeError(
                "PostgreSQL is not linked to this Railway service: "
                f"{variable} points to localhost. {fix}"
            )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_database_configured()
    return settings
