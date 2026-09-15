from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentMethod, PaymentStatus, ReservationStatus
from app.models.fleet import Seat
from app.models.trip import Trip


class Reservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_reservations_public_code", "public_code", unique=True),
        Index("ix_reservations_contact_phone", "contact_phone"),
        Index("ix_reservations_status", "status"),
        Index("ix_reservations_trip_status", "trip_id", "status"),
        Index("ix_reservations_company", "company_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    trip_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("trips.id"), nullable=False, index=True
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transport_companies.id"), nullable=False
    )
    public_code: Mapped[str] = mapped_column(String(16), nullable=False)
    booking_request_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    status: Mapped[ReservationStatus] = mapped_column(nullable=False, default=ReservationStatus.pending)
    payment_status: Mapped[PaymentStatus] = mapped_column(nullable=False, default=PaymentStatus.unpaid)
    payment_method: Mapped[PaymentMethod | None] = mapped_column()
    total_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    deposit_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deposit_received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminder_day_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminder_soon_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trip: Mapped[Trip] = relationship()
    seats: Mapped[list["ReservationSeat"]] = relationship(back_populates="reservation")
    passengers: Mapped[list["ReservationPassenger"]] = relationship(back_populates="reservation")
    payments: Mapped[list["Payment"]] = relationship(back_populates="reservation")  # noqa: F821


class ReservationSeat(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reservation_seats"
    __table_args__ = (
        Index(
            "uq_active_trip_seat",
            "trip_id",
            "seat_id",
            unique=True,
            postgresql_where=text("is_active_hold = true"),
        ),
        Index("ix_reservation_seats_reservation", "reservation_id"),
    )

    reservation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reservations.id"), nullable=False
    )
    trip_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("trips.id"), nullable=False
    )
    seat_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seats.id"), nullable=False
    )
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    reservation: Mapped[Reservation] = relationship(back_populates="seats")
    seat: Mapped[Seat] = relationship()


class ReservationPassenger(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reservation_passengers"

    reservation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reservations.id"), nullable=False, index=True
    )
    seat_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seats.id"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    document_type: Mapped[str | None] = mapped_column(String(32))
    document_number: Mapped[str | None] = mapped_column(String(64))
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gender: Mapped[str | None] = mapped_column(String(16))
    nationality: Mapped[str | None] = mapped_column(String(2))

    reservation: Mapped[Reservation] = relationship(back_populates="passengers")
    seat: Mapped[Seat] = relationship()
