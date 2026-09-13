from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus, ReservationStatus, TicketStatus
from app.schemas.common import ORMModel


class PassengerIn(BaseModel):
    seat_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = None
    phone: str | None = None
    document_type: str | None = None
    document_number: str | None = None


class ReservationCreateIn(BaseModel):
    trip_id: UUID
    seat_ids: list[UUID]
    contact_phone: str
    passengers: list[PassengerIn]


class ReservationSeatOut(ORMModel):
    seat_id: UUID
    price_minor: int
    is_active_hold: bool
    seat_number: str | None = None


class ReservationPassengerOut(ORMModel):
    id: UUID
    seat_id: UUID
    first_name: str
    last_name: str | None
    phone: str | None
    document_type: str | None
    document_number: str | None


class PaymentOut(ORMModel):
    id: UUID
    reservation_id: UUID
    provider: str
    method: PaymentMethod
    amount_minor: int
    currency: str
    status: PaymentStatus
    provider_payment_id: str | None
    created_at: datetime
    paid_at: datetime | None


class ReservationOut(ORMModel):
    id: UUID
    public_code: str
    trip_id: UUID
    company_id: UUID
    status: ReservationStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    total_amount_minor: int
    currency: str
    expires_at: datetime | None
    contact_phone: str
    deposit_required: bool
    deposit_received: bool
    created_at: datetime
    seats: list[ReservationSeatOut] = []
    passengers: list[ReservationPassengerOut] = []
    payments: list[PaymentOut] = []


class BookingLookupIn(BaseModel):
    phone: str
    public_code: str


class PaymentCreateIn(BaseModel):
    method: PaymentMethod
    provider: str = "mock"


class TicketOut(ORMModel):
    id: UUID
    public_id: str
    qr_token: str
    reservation_id: UUID
    trip_id: UUID
    seat_id: UUID
    status: TicketStatus
    passenger: ReservationPassengerOut | None = None
    seat_number: str | None = None


class TicketVerifyIn(BaseModel):
    qr_token: str


class CompanyOut(ORMModel):
    id: UUID
    name: str
    phone: str
    active: bool


class CompanyIn(BaseModel):
    name: str
    phone: str
    active: bool = True


class UserAdminOut(ORMModel):
    id: UUID
    phone: str
    first_name: str | None
    last_name: str | None
    email: str | None
    role: str
    status: str
    phone_verified: bool
    company_id: UUID | None
    created_at: datetime


class DashboardOut(BaseModel):
    trips_today: int
    passengers_today: int
    sold_seats: int
    free_seats: int
    pending_approvals: int
    unpaid: int
    large_bookings: int


class PageReservations(BaseModel):
    items: list[ReservationOut]
    page: int
    page_size: int
    total: int


class PagePayments(BaseModel):
    items: list[PaymentOut]
    page: int
    page_size: int
    total: int


class PagePassengers(BaseModel):
    items: list[ReservationPassengerOut]
    page: int
    page_size: int
    total: int


class PageUsers(BaseModel):
    items: list[UserAdminOut]
    page: int
    page_size: int
    total: int


class PageCompanies(BaseModel):
    items: list[CompanyOut]
    page: int
    page_size: int
    total: int
