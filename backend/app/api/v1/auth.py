from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.schemas.auth import (
    AdminLoginRequest,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", response_model=OtpRequestResponse)
async def request_otp(body: OtpRequest, session: AsyncSession = Depends(db_session)):
    code = await AuthService(session).request_otp(body.phone)
    return OtpRequestResponse(ok=True, dev_code=code)


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(body: OtpVerifyRequest, session: AsyncSession = Depends(db_session)):
    data = await AuthService(session).verify_otp(body.phone, body.code)
    return TokenResponse.model_validate(data)


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(body: AdminLoginRequest, session: AsyncSession = Depends(db_session)):
    data = await AuthService(session).admin_login(body.email, body.password)
    return TokenResponse.model_validate(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(db_session)):
    data = await AuthService(session).refresh(body.refresh_token)
    return TokenResponse.model_validate(data)
