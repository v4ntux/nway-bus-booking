from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import PaymentMethod, PaymentStatus
from app.models.reservation import Reservation


class Payment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payments"

    reservation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reservations.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(nullable=False, default=PaymentStatus.pending)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128))
    extra_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reservation: Mapped[Reservation] = relationship(back_populates="payments")
