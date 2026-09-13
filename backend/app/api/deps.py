from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_session
from app.models import User, UserRole, UserStatus
from app.services.auth import AuthService


async def db_session(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


async def optional_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(db_session),
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    return await AuthService(session).get_user(UUID(payload["sub"]))


async def current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(db_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError()
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc), "Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("TOKEN_INVALID", "Invalid token")
    user = await AuthService(session).get_user(UUID(payload["sub"]))
    if user.status == UserStatus.blocked:
        raise ForbiddenError("USER_BLOCKED", "Account is blocked")
    return user


def require_roles(*roles: UserRole):
    async def _inner(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError("FORBIDDEN", "Insufficient permissions")
        return user

    return _inner


StaffUser = require_roles(UserRole.operator, UserRole.admin, UserRole.superadmin)
AdminUser = require_roles(UserRole.admin, UserRole.superadmin)
