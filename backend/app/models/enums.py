import enum


class UserRole(str, enum.Enum):
    passenger = "passenger"
    driver = "driver"
    operator = "operator"
    admin = "admin"
    superadmin = "superadmin"


class UserStatus(str, enum.Enum):
    active = "active"
    blocked = "blocked"


class SeatType(str, enum.Enum):
    standard = "standard"
    premium = "premium"
    child = "child"
    accessibility = "accessibility"
    blocked = "blocked"


class LayoutCellType(str, enum.Enum):
    seat = "seat"
    aisle = "aisle"
    driver = "driver"
    door = "door"
    stairs = "stairs"
    toilet = "toilet"
    empty = "empty"
    service = "service"


class TripStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    boarding = "boarding"
    departed = "departed"
    completed = "completed"
    cancelled = "cancelled"


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    awaiting_deposit = "awaiting_deposit"
    awaiting_admin_approval = "awaiting_admin_approval"
    confirmed = "confirmed"
    cancelled = "cancelled"
    expired = "expired"
    completed = "completed"
    no_show = "no_show"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    pending = "pending"
    partially_paid = "partially_paid"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"


class PaymentMethod(str, enum.Enum):
    online = "online"
    cash = "cash"
    transfer = "transfer"
    deposit = "deposit"
    other = "other"


class TicketStatus(str, enum.Enum):
    valid = "valid"
    used = "used"
    cancelled = "cancelled"


ACTIVE_RESERVATION_STATUSES: frozenset[ReservationStatus] = frozenset(
    {
        ReservationStatus.pending,
        ReservationStatus.awaiting_deposit,
        ReservationStatus.awaiting_admin_approval,
        ReservationStatus.confirmed,
    }
)

BOOKABLE_TRIP_STATUSES: frozenset[TripStatus] = frozenset(
    {TripStatus.scheduled, TripStatus.boarding}
)

TERMINAL_RESERVATION_STATUSES: frozenset[ReservationStatus] = frozenset(
    {
        ReservationStatus.cancelled,
        ReservationStatus.expired,
        ReservationStatus.completed,
        ReservationStatus.no_show,
    }
)
