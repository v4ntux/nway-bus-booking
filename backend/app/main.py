import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1 import admin_router, auth_router, public_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    settings = get_settings()
    task = None
    bot = None
    if settings.telegram_ready:
        from app.db.session import SessionLocal, engine
        from app.services.telegram_bot import TelegramBotClient
        from app.services.telegram_worker import run_worker
        bot = TelegramBotClient(settings.TELEGRAM_BOT_TOKEN)
        task = asyncio.create_task(run_worker(bot, SessionLocal, engine))
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        if bot:
            await bot.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NWay Booking API",
        version="0.1.0",
        description=(
            "Intercity bus seat-booking platform. "
            "Money is stored as integer minor units (1/100 of the currency, e.g. 1500000 = 15000.00 UZS). "
            "All timestamps are UTC. Public booking codes are shown to passengers, never database UUIDs."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(public_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    from app.api.telegram import router as telegram_router
    app.include_router(telegram_router)
    return app


app = create_app()
