from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.base import Base
from app.models.enums import UserRole, UserStatus


class TransportCompany(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transport_companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.passenger)
    status: Mapped[UserStatus] = mapped_column(nullable=False, default=UserStatus.active)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    company_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transport_companies.id")
    )

    company: Mapped[TransportCompany | None] = relationship()
    stats: Mapped["UserStats | None"] = relationship(back_populates="user", uselist=False)


class UserStats(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_stats"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    completed_trips: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancelled_reservations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    no_show_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    user: Mapped[User] = relationship(back_populates="stats")
