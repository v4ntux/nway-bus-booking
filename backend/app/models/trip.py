from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TripStatus
from app.models.fleet import Bus
from app.models.route import Route


class Trip(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trips"
    __table_args__ = (
        Index("ix_trips_departure", "departure_datetime"),
        Index("ix_trips_route_departure", "route_id", "departure_datetime"),
        Index("ix_trips_company_status", "company_id", "status"),
    )

    route_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("routes.id"), nullable=False, index=True
    )
    bus_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("buses.id"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transport_companies.id"), nullable=False, index=True
    )
    driver_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    departure_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_arrival_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TripStatus] = mapped_column(nullable=False, default=TripStatus.scheduled)
    base_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    boarding_location: Mapped[str | None] = mapped_column(String(255))
    destination_location: Mapped[str | None] = mapped_column(Text)

    route: Mapped[Route] = relationship()
    bus: Mapped[Bus] = relationship()
