from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.telegram_auth import optional_telegram_user
from app.models.telegram import TelegramChat, TelegramDelivery
from app.api.deps import db_session, optional_user, require_roles
from app.core.exceptions import DomainError, NotFoundError, ForbiddenError, UnauthorizedError
from app.api.serializers import reservation_to_out, ticket_to_out
from app.models import City, PaymentStatus, ReservationSeat, ReservationStatus, Route, Trip, User, UserRole, Ticket, Reservation
from app.schemas.booking import (
    BookingLookupIn,
    MyReservationOut,
    MyTicketOut,
    PaymentCreateIn,
    PaymentOut,
    ReservationCreateIn,
    ReservationOut,
    TicketOut,
    TicketVerifyIn,
    TripBriefOut,
)
from app.schemas.catalog import CityOut, RouteOut, TripOut, TripSearchOut, TripSeatMapOut
from app.schemas.faq import FaqOut
from app.services.faq import list_faq
from app.services.payment import PaymentService
from app.services.reservation import PassengerInput, ReservationService, SeatMapService, queue_telegram_tickets
from app.services.ticket import TicketService
from app.services.trip import TripService
from app.utils.phone import normalize_phone
from app.utils.time import utcnow

router = APIRouter(tags=["public"])


def booking_phone(x_booking_phone: str | None = Header(default=None)) -> str | None:
    """Contact phone of a web (non-Telegram) booking; the code alone must not grant access."""
    if not x_booking_phone:
        return None
    try:
        return normalize_phone(x_booking_phone)
    except DomainError:
        return None


def protect_booking(reservation, user, telegram_id=None, phone=None):
    if user and (user.role == UserRole.superadmin or
                 (user.role in {UserRole.admin, UserRole.operator} and user.company_id == reservation.company_id)):
        return
    if reservation.telegram_chat_id is not None:
        if telegram_id is not None and telegram_id == reservation.telegram_chat_id:
            return
    elif phone is not None and phone == reservation.contact_phone:
        return
    # Same answer as a wrong code, so codes cannot be probed.
    raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")


def can_cancel(reservation, trip) -> bool:
    return (reservation.status in {ReservationStatus.pending, ReservationStatus.confirmed, ReservationStatus.awaiting_admin_approval}
            and reservation.payment_status == PaymentStatus.unpaid and trip.departure_datetime > utcnow())


@router.get("/cities", response_model=list[CityOut], summary="List active cities")
async def list_cities(session: AsyncSession = Depends(db_session)):
    result = await session.execute(select(City).where(City.active.is_(True)).order_by(City.name))
    return [CityOut.model_validate(c) for c in result.scalars().all()]


@router.get("/routes", response_model=list[RouteOut], summary="List active routes")
async def list_routes(session: AsyncSession = Depends(db_session)):
    result = await session.execute(
        select(Route)
        .options(selectinload(Route.origin_city), selectinload(Route.destination_city))
        .where(Route.active.is_(True))
    )
    return [RouteOut.model_validate(r) for r in result.scalars().all()]


@router.get("/trips", response_model=TripSearchOut, summary="Search trips by origin, destination and date")
async def search_trips(
    origin_city_id: UUID,
    destination_city_id: UUID,
    travel_date: date,
    session: AsyncSession = Depends(db_session),
):
    rows = await TripService(session).search(origin_city_id, destination_city_id, travel_date)
    items = []
    for row in rows:
        trip = row["trip"]
        payload = TripOut.model_validate(trip)
        payload.available_seats = row["available_seats"]
        payload.route = RouteOut.model_validate(trip.route)
        from app.schemas.catalog import BusOut

        payload.bus = BusOut.model_validate(trip.bus)
        items.append(payload)
    return TripSearchOut(items=items)


@router.get("/trips/{trip_id}", response_model=TripOut)
async def get_trip(trip_id: UUID, session: AsyncSession = Depends(db_session)):
    service = TripService(session)
    trip = await service.get(trip_id)
    payload = TripOut.model_validate(trip)
    payload.available_seats = await service.available_seats_count(trip)
    payload.route = RouteOut.model_validate(trip.route)
    from app.schemas.catalog import BusOut

    payload.bus = BusOut.model_validate(trip.bus)
    return payload


@router.get("/trips/{trip_id}/seats", response_model=TripSeatMapOut)
async def trip_seats(trip_id: UUID, session: AsyncSession = Depends(db_session)):
    data = await SeatMapService(session).trip_seat_map(trip_id)
    return TripSeatMapOut.model_validate(data)


@router.post("/reservations", response_model=ReservationOut, status_code=201)
async def create_reservation(
    body: ReservationCreateIn,
    session: AsyncSession = Depends(db_session),
    user: User | None = Depends(optional_user),
    telegram_id: int | None = Depends(optional_telegram_user),
):
    if telegram_id:
        # Serialize submissions from one chat, including retries after a lost response.
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": telegram_id})
        await session.execute(insert(TelegramChat).values(chat_id=telegram_id, data={}).on_conflict_do_nothing())
    reservation = await ReservationService(session).create(
        trip_id=body.trip_id,
        seat_ids=body.seat_ids,
        contact_phone=body.contact_phone,
        passengers=[PassengerInput(**p.model_dump()) for p in body.passengers],
        user_id=user.id if user else None,
        telegram_chat_id=telegram_id,
        booking_request_key=f"miniapp:{telegram_id}:{body.request_key}" if telegram_id and body.request_key else None,
    )
    return reservation_to_out(reservation)


@router.get("/me/reservations", response_model=list[MyReservationOut], summary="Bookings of the Telegram Mini App user")
async def my_reservations(session: AsyncSession = Depends(db_session), telegram_id: int | None = Depends(optional_telegram_user)):
    if telegram_id is None:
        raise UnauthorizedError("TELEGRAM_AUTH_REQUIRED", "Open NWay from Telegram")
    reservations = list((await session.scalars(
        select(Reservation)
        .options(
            selectinload(Reservation.seats).selectinload(ReservationSeat.seat),
            selectinload(Reservation.passengers),
            selectinload(Reservation.payments),
            selectinload(Reservation.trip).selectinload(Trip.route).selectinload(Route.origin_city),
            selectinload(Reservation.trip).selectinload(Trip.route).selectinload(Route.destination_city),
        )
        .where(Reservation.telegram_chat_id == telegram_id)
        .order_by(Reservation.created_at.desc())
        .limit(30)
    )).all())
    tickets = list((await session.scalars(
        select(Ticket).options(selectinload(Ticket.seat), selectinload(Ticket.passenger))
        .where(Ticket.reservation_id.in_([r.id for r in reservations]))
    )).all()) if reservations else []
    items = []
    for reservation in reservations:
        trip, route = reservation.trip, reservation.trip.route
        base = reservation_to_out(reservation).model_dump()
        items.append(MyReservationOut(
            **base,
            trip=TripBriefOut(
                departure_datetime=trip.departure_datetime,
                estimated_arrival_datetime=trip.estimated_arrival_datetime,
                origin_city=route.origin_city.name,
                destination_city=route.destination_city.name,
                origin_timezone=route.origin_city.timezone,
                destination_timezone=route.destination_city.timezone,
                boarding_location=trip.boarding_location,
            ),
            tickets=[
                MyTicketOut(
                    public_id=ticket.public_id,
                    seat_number=ticket.seat.seat_number if ticket.seat else None,
                    status=ticket.status,
                    passenger_name=" ".join(filter(None, [ticket.passenger.first_name, ticket.passenger.last_name])) if ticket.passenger else "",
                )
                for ticket in tickets if ticket.reservation_id == reservation.id
            ],
            can_cancel=can_cancel(reservation, trip),
        ))
    return items


@router.get("/reservations/{public_code}", response_model=ReservationOut)
async def get_reservation(public_code: str, session: AsyncSession = Depends(db_session), user: User | None = Depends(optional_user),
                          telegram_id: int | None = Depends(optional_telegram_user), phone: str | None = Depends(booking_phone)):
    reservation = await ReservationService(session).get_by_public_code(public_code)
    protect_booking(reservation, user, telegram_id, phone)
    return reservation_to_out(reservation)


@router.post("/reservations/{public_code}/cancel", response_model=ReservationOut)
async def cancel_reservation(public_code: str, session: AsyncSession = Depends(db_session), user: User | None = Depends(optional_user),
                             telegram_id: int | None = Depends(optional_telegram_user), phone: str | None = Depends(booking_phone)):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
    protect_booking(reservation, user, telegram_id, phone)
    trip = await session.get(Trip, reservation.trip_id)
    if not can_cancel(reservation, trip):
        raise DomainError("CANCEL_UNAVAILABLE", "This booking can no longer be cancelled online", 409)
    reservation = await service.cancel(reservation.id, actor_id=None)
    return reservation_to_out(reservation)


@router.post("/reservations/{public_code}/telegram-resend", status_code=202)
async def resend_telegram_tickets(public_code: str, session: AsyncSession = Depends(db_session),
                                  telegram_id: int | None = Depends(optional_telegram_user)):
    reservation = await ReservationService(session).get_by_public_code(public_code)
    if telegram_id is None or reservation.telegram_chat_id != telegram_id:
        raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
    if reservation.status != ReservationStatus.confirmed:
        raise DomainError("TICKET_INACTIVE", "Tickets are not active for this booking", 409)
    await queue_telegram_tickets(session, reservation.id, telegram_id, resend=True)
    await session.commit()
    return {"queued": True}


@router.post("/reservations/{public_code}/payments", response_model=PaymentOut, status_code=201)
async def create_payment(
    public_code: str,
    body: PaymentCreateIn,
    session: AsyncSession = Depends(db_session),
    user: User | None = Depends(optional_user),
    telegram_id: int | None = Depends(optional_telegram_user),
    phone: str | None = Depends(booking_phone),
):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
    protect_booking(reservation, user, telegram_id, phone)
    payment = await PaymentService(session).create_for_reservation(
        reservation.id, body.method, provider_name=body.provider
    )
    return PaymentOut.model_validate(payment)


@router.post("/payments/{payment_id}/mock-success", response_model=PaymentOut)
async def mock_payment_success(payment_id: UUID, session: AsyncSession = Depends(db_session)):
    payment = await PaymentService(session).mock_success(payment_id)
    return PaymentOut.model_validate(payment)


@router.post("/payments/{payment_id}/mock-fail", response_model=PaymentOut)
async def mock_payment_fail(payment_id: UUID, session: AsyncSession = Depends(db_session)):
    payment = await PaymentService(session).mock_fail(payment_id)
    return PaymentOut.model_validate(payment)


@router.post("/bookings/lookup", response_model=ReservationOut)
async def lookup_booking(body: BookingLookupIn, session: AsyncSession = Depends(db_session), user: User | None = Depends(optional_user), telegram_id: int | None = Depends(optional_telegram_user)):
    reservation = await ReservationService(session).lookup(body.phone, body.public_code)
    # Phone + code already match for web bookings; Telegram bookings stay private to their chat.
    protect_booking(reservation, user, telegram_id, reservation.contact_phone)
    return reservation_to_out(reservation)


@router.get("/tickets/{public_id}", response_model=TicketOut)
async def get_ticket(public_id: str, session: AsyncSession = Depends(db_session), user: User | None = Depends(optional_user),
                     telegram_id: int | None = Depends(optional_telegram_user), phone: str | None = Depends(booking_phone)):
    ticket = await TicketService(session).get_by_public_id(public_id)
    protect_booking(ticket.reservation, user, telegram_id, phone)
    return ticket_to_out(ticket)


@router.post("/tickets/verify", response_model=TicketOut, summary="Verify QR token and mark ticket used")
async def verify_ticket(body: TicketVerifyIn, session: AsyncSession = Depends(db_session), actor: User = Depends(require_roles(UserRole.driver, UserRole.operator, UserRole.admin, UserRole.superadmin))):
    reservation = await session.scalar(select(Reservation).join(Ticket, Ticket.reservation_id == Reservation.id).where(Ticket.qr_token == body.qr_token.strip()))
    if not reservation:
        raise NotFoundError("TICKET_NOT_FOUND", "Ticket not found")
    if actor.role != UserRole.superadmin and actor.company_id != reservation.company_id:
        raise ForbiddenError("FORBIDDEN", "Ticket belongs to another company")
    ticket = await TicketService(session).verify_qr(body.qr_token)
    return ticket_to_out(ticket)


@router.get("/reservations/{public_code}/tickets", response_model=list[TicketOut])
async def reservation_tickets(public_code: str, session: AsyncSession = Depends(db_session), user: User | None = Depends(optional_user),
                              telegram_id: int | None = Depends(optional_telegram_user), phone: str | None = Depends(booking_phone)):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
    protect_booking(reservation, user, telegram_id, phone)
    tickets = await TicketService(session).list_for_reservation(reservation.id)
    return [ticket_to_out(t) for t in tickets]


@router.get("/faq", response_model=list[FaqOut], summary="Active FAQ entries for a language")
async def faq(lang: str = Query("uz"), session: AsyncSession = Depends(db_session)):
    return [FaqOut.model_validate(item) for item in await list_faq(session, lang)]


@router.get("/app-config")
async def app_config():
    settings = get_settings()
    return {
        "demo_mode": settings.TELEGRAM_DEMO_MODE,
        "payment_methods": ["cash"],
        "bot_username": settings.TELEGRAM_BOT_USERNAME.lstrip("@") or None,
        "support_contact": settings.TELEGRAM_SUPPORT or None,
        "support_chat": bool(settings.TELEGRAM_SUPPORT_CHAT_ID),
    }


@router.post("/reservations/{public_code}/confirm-cash", response_model=ReservationOut)
async def confirm_cash(public_code: str, session: AsyncSession = Depends(db_session),
                       user: User | None = Depends(optional_user),
                       telegram_id: int | None = Depends(optional_telegram_user),
                       phone: str | None = Depends(booking_phone)):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
    protect_booking(reservation, user, telegram_id, phone)
    return reservation_to_out(await service.confirm_cash(reservation.id))


@router.get("/reservations/{public_code}/telegram-delivery")
async def telegram_delivery(public_code: str, session: AsyncSession = Depends(db_session),
                            telegram_id: int | None = Depends(optional_telegram_user)):
    reservation = await ReservationService(session).get_by_public_code(public_code)
    if telegram_id is None or reservation.telegram_chat_id != telegram_id:
        raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
    deliveries = list((await session.scalars(select(TelegramDelivery).join(Ticket).where(
        Ticket.reservation_id == reservation.id))).all())
    return {"total": len(deliveries), "sent": sum(d.sent_at is not None for d in deliveries),
            "failed": any(d.attempts >= 8 and d.sent_at is None for d in deliveries)}
