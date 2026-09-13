from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TicketStatus
from app.models.reservation import Reservation, ReservationPassenger
from app.models.fleet import Seat
from app.models.trip import Trip


class Ticket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tickets"

    public_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    reservation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reservations.id"), nullable=False, index=True
    )
    passenger_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reservation_passengers.id"), nullable=False
    )
    trip_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    seat_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("seats.id"), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(nullable=False, default=TicketStatus.valid)

    reservation: Mapped[Reservation] = relationship()
    passenger: Mapped[ReservationPassenger] = relationship()
    trip: Mapped[Trip] = relationship()
    seat: Mapped[Seat] = relationship()
