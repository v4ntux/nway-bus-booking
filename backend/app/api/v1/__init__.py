from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.public import router as public_router

__all__ = ["admin_router", "auth_router", "public_router"]
