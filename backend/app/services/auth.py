from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import DomainError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.rate_limit import rate_limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import OtpChallenge, RefreshToken, User, UserRole, UserStats, UserStatus
from app.services.sms import sms_provider
from app.utils.phone import normalize_phone
from app.utils.time import utcnow


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def request_otp(self, phone_raw: str) -> str | None:
        phone = normalize_phone(phone_raw)
        await rate_limiter.check(f"otp:{phone}", limit=5, window_seconds=300)
        code = sms_provider.generate_code(self.settings.OTP_CODE_LENGTH)
        now = utcnow()
        challenge = OtpChallenge(
            phone=phone,
            code_hash=hash_password(code),
            expires_at=now + timedelta(minutes=self.settings.OTP_EXPIRE_MINUTES),
            created_at=now,
        )
        self.session.add(challenge)
        await sms_provider.send(phone, code)
        await self.session.commit()
        return code if self.settings.DEBUG else None

    async def verify_otp(self, phone_raw: str, code: str) -> dict:
        phone = normalize_phone(phone_raw)
        result = await self.session.execute(
            select(OtpChallenge)
            .where(OtpChallenge.phone == phone, OtpChallenge.consumed_at.is_(None))
            .order_by(OtpChallenge.created_at.desc())
        )
        challenge = result.scalars().first()
        if challenge is None or challenge.expires_at < utcnow():
            raise DomainError("OTP_INVALID", "Invalid or expired code")
        challenge.attempts += 1
        if challenge.attempts > 5:
            raise DomainError("OTP_LOCKED", "Too many attempts")
        if not verify_password(code, challenge.code_hash):
            await self.session.commit()
            raise DomainError("OTP_INVALID", "Invalid or expired code")
        challenge.consumed_at = utcnow()

        user_result = await self.session.execute(select(User).where(User.phone == phone))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(
                phone=phone,
                role=UserRole.passenger,
                status=UserStatus.active,
                phone_verified=True,
            )
            self.session.add(user)
            await self.session.flush()
            self.session.add(UserStats(user_id=user.id))
        else:
            if user.status == UserStatus.blocked:
                raise ForbiddenError("USER_BLOCKED", "Account is blocked")
            user.phone_verified = True
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def admin_login(self, email: str, password: str) -> dict:
        await rate_limiter.check(f"login:{email.lower()}", limit=10, window_seconds=300)
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if (
            user is None
            or not user.password_hash
            or not verify_password(password, user.password_hash)
        ):
            raise UnauthorizedError("INVALID_CREDENTIALS", "Invalid email or password")
        if user.status == UserStatus.blocked:
            raise ForbiddenError("USER_BLOCKED", "Account is blocked")
        if user.role not in {UserRole.admin, UserRole.superadmin, UserRole.operator}:
            raise ForbiddenError("NOT_STAFF", "Staff login required")
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError(str(exc), "Invalid refresh token") from exc
        if payload.get("type") != "refresh":
            raise UnauthorizedError("TOKEN_INVALID", "Invalid refresh token")
        token_id = UUID(payload["jti"])
        stored = await self.session.get(RefreshToken, token_id)
        if stored is None or stored.revoked_at is not None or stored.expires_at < utcnow():
            raise UnauthorizedError("TOKEN_INVALID", "Invalid refresh token")
        user = await self.session.get(User, stored.user_id)
        if user is None or user.status == UserStatus.blocked:
            raise UnauthorizedError("TOKEN_INVALID", "Invalid refresh token")
        stored.revoked_at = utcnow()
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def _issue_tokens(self, user: User) -> dict:
        token_row = RefreshToken(
            id=uuid4(),
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=self.settings.JWT_REFRESH_EXPIRE_DAYS),
            created_at=utcnow(),
        )
        self.session.add(token_row)
        await self.session.flush()
        return {
            "access_token": create_access_token(user.id, user.role.value, user.company_id),
            "refresh_token": create_refresh_token(user.id, token_row.id),
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "phone": user.phone,
                "email": user.email,
                "role": user.role.value,
                "company_id": str(user.company_id) if user.company_id else None,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }

    async def get_user(self, user_id: UUID) -> User:
        result = await self.session.execute(
            select(User).options(selectinload(User.stats)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", "User not found")
        return user
