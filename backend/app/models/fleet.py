from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LayoutCellType, SeatType


class Bus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "buses"

    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transport_companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    seat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    layout_type: Mapped[str] = mapped_column(String(32), nullable=False, default="2+2")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    seats: Mapped[list["Seat"]] = relationship(back_populates="bus")
    layout: Mapped["BusLayout | None"] = relationship(back_populates="bus", uselist=False)


class Seat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seats"

    bus_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("buses.id"), nullable=False, index=True
    )
    seat_number: Mapped[str] = mapped_column(String(16), nullable=False)
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    column: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[SeatType] = mapped_column(nullable=False, default=SeatType.standard)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_accessibility: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_child: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Front rows reserved for women travelling alone. Advisory: the platform
    # never asks for gender, so this labels the seat rather than gating it.
    is_women_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    bus: Mapped[Bus] = relationship(back_populates="seats")


class BusLayout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bus_layouts"

    bus_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("buses.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="Default")
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    columns: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    bus: Mapped[Bus] = relationship(back_populates="layout")
    cells: Mapped[list["LayoutCell"]] = relationship(back_populates="layout")


class LayoutCell(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "layout_cells"
    __table_args__ = (CheckConstraint('"row" >= 0 AND "column" >= 0', name="ck_layout_cell_nonneg"),)

    layout_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("bus_layouts.id"), nullable=False, index=True
    )
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    column: Mapped[int] = mapped_column(Integer, nullable=False)
    cell_type: Mapped[LayoutCellType] = mapped_column(nullable=False)
    seat_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("seats.id"))
    x: Mapped[int | None] = mapped_column(Integer)
    y: Mapped[int | None] = mapped_column(Integer)

    layout: Mapped[BusLayout] = relationship(back_populates="cells")
    seat: Mapped[Seat | None] = relationship()
