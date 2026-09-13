from datetime import timedelta
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.geo import City


class Route(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint("company_id", "origin_city_id", "destination_city_id"),)

    origin_city_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cities.id"), nullable=False, index=True
    )
    destination_city_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cities.id"), nullable=False, index=True
    )
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_km: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transport_companies.id"), nullable=False, index=True
    )

    origin_city: Mapped[City] = relationship(foreign_keys=[origin_city_id])
    destination_city: Mapped[City] = relationship(foreign_keys=[destination_city_id])
    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="route", order_by="RouteStop.order_index"
    )

    @property
    def estimated_duration(self) -> timedelta:
        return timedelta(minutes=self.estimated_duration_minutes)


class RouteStop(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "route_stops"
    __table_args__ = (UniqueConstraint("route_id", "order_index"),)

    route_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("routes.id"), nullable=False, index=True
    )
    city_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("cities.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    departure_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    route: Mapped[Route] = relationship(back_populates="stops")
    city: Mapped[City] = relationship()
