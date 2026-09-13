from contextlib import asynccontextmanager

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
    yield


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
    return app


app = create_app()
