from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import UserRole
from app.schemas.common import ORMModel


class OtpRequest(BaseModel):
    phone: str


class OtpRequestResponse(BaseModel):
    ok: bool = True
    dev_code: str | None = None


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=8)


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(ORMModel):
    id: UUID
    phone: str
    email: str | None
    role: UserRole
    company_id: UUID | None
    first_name: str | None
    last_name: str | None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic
