from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import LayoutCellType, SeatType, TripStatus
from app.schemas.common import ORMModel


class CityOut(ORMModel):
    id: UUID
    name: str
    country: str
    timezone: str
    lat: float | None
    lng: float | None
    active: bool


class CityIn(BaseModel):
    name: str
    country: str = Field(min_length=2, max_length=2)
    timezone: str = "UTC"
    lat: float | None = None
    lng: float | None = None
    active: bool = True


class RouteOut(ORMModel):
    id: UUID
    origin_city_id: UUID
    destination_city_id: UUID
    origin_city: CityOut | None = None
    destination_city: CityOut | None = None
    estimated_duration_minutes: int
    distance_km: int
    description: str | None
    active: bool
    company_id: UUID


class RouteIn(BaseModel):
    origin_city_id: UUID
    destination_city_id: UUID
    estimated_duration_minutes: int
    distance_km: int
    description: str | None = None
    company_id: UUID | None = None
    active: bool = True


class BusOut(ORMModel):
    id: UUID
    company_id: UUID
    name: str
    registration_number: str
    model: str
    seat_count: int
    layout_type: str
    active: bool


class BusIn(BaseModel):
    name: str
    registration_number: str
    model: str
    seat_count: int
    layout_type: str = "2+2"
    company_id: UUID | None = None
    active: bool = True


class SeatOut(ORMModel):
    id: UUID
    bus_id: UUID
    seat_number: str
    row: int
    column: int
    type: SeatType
    active: bool
    is_accessibility: bool
    is_child: bool
    is_premium: bool
    is_blocked: bool
    is_women_only: bool = False


class LayoutCellOut(ORMModel):
    id: UUID | None = None
    row: int
    column: int
    cell_type: LayoutCellType
    seat_id: UUID | None = None
    x: int | None = None
    y: int | None = None


class LayoutCellPatch(BaseModel):
    row: int
    column: int
    cell_type: LayoutCellType


class LayoutGenerateIn(BaseModel):
    """Build (or rebuild) a coach layout from a few geometry parameters."""

    name: str = "2+2 coach"
    rows: int = Field(13, ge=2, le=30)
    columns: int = Field(5, ge=2, le=8)
    aisle_columns: list[int] = [2]
    door_cells: list[tuple[int, int]] = [(1, 3), (1, 4), (11, 3), (11, 4)]
    full_width_rows: list[int] = [12]
    women_rows: list[int] = [0, 1, 2, 3]


class TripPatchIn(BaseModel):
    departure_datetime: datetime | None = None
    base_price_minor: int | None = Field(None, ge=0)
    status: TripStatus | None = None
    boarding_location: str | None = None
    destination_location: str | None = None


class BusLayoutOut(ORMModel):
    id: UUID
    bus_id: UUID
    name: str
    rows: int
    columns: int
    active: bool
    cells: list[LayoutCellOut] = []


class TripOut(ORMModel):
    id: UUID
    route_id: UUID
    bus_id: UUID
    company_id: UUID
    driver_id: UUID | None
    departure_datetime: datetime
    estimated_arrival_datetime: datetime
    status: TripStatus
    base_price_minor: int
    currency: str
    boarding_location: str | None
    destination_location: str | None
    available_seats: int | None = None
    route: RouteOut | None = None
    bus: BusOut | None = None


class TripSearchOut(BaseModel):
    items: list[TripOut]


class TripCreateIn(BaseModel):
    route_id: UUID
    bus_id: UUID
    departure_datetime: datetime
    base_price_minor: int
    currency: str | None = None
    boarding_location: str | None = None
    destination_location: str | None = None
    company_id: UUID | None = None
    status: TripStatus = TripStatus.scheduled


class TripBusChangeIn(BaseModel):
    bus_id: UUID


class SeatStatusOut(BaseModel):
    id: UUID
    seat_number: str
    type: str
    status: str
    is_accessibility: bool
    is_premium: bool
    is_women_only: bool = False


class SeatCellOut(BaseModel):
    row: int
    column: int
    cell_type: str
    seat: SeatStatusOut | None = None


class TripSeatMapOut(BaseModel):
    trip_id: UUID
    rows: int
    columns: int
    cells: list[SeatCellOut]
