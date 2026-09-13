from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import db_session, optional_user
from app.api.serializers import reservation_to_out, ticket_to_out
from app.models import City, Route, User
from app.schemas.booking import (
    BookingLookupIn,
    PaymentCreateIn,
    PaymentOut,
    ReservationCreateIn,
    ReservationOut,
    TicketOut,
    TicketVerifyIn,
)
from app.schemas.catalog import CityOut, RouteOut, TripOut, TripSearchOut, TripSeatMapOut
from app.services.payment import PaymentService
from app.services.reservation import PassengerInput, ReservationService, SeatMapService
from app.services.ticket import TicketService
from app.services.trip import TripService

router = APIRouter(tags=["public"])


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
):
    reservation = await ReservationService(session).create(
        trip_id=body.trip_id,
        seat_ids=body.seat_ids,
        contact_phone=body.contact_phone,
        passengers=[PassengerInput(**p.model_dump()) for p in body.passengers],
        user_id=user.id if user else None,
    )
    return reservation_to_out(reservation)


@router.get("/reservations/{public_code}", response_model=ReservationOut)
async def get_reservation(public_code: str, session: AsyncSession = Depends(db_session)):
    reservation = await ReservationService(session).get_by_public_code(public_code)
    return reservation_to_out(reservation)


@router.post("/reservations/{public_code}/cancel", response_model=ReservationOut)
async def cancel_reservation(public_code: str, session: AsyncSession = Depends(db_session)):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
    reservation = await service.cancel(reservation.id, actor_id=None)
    return reservation_to_out(reservation)


@router.post("/reservations/{public_code}/payments", response_model=PaymentOut, status_code=201)
async def create_payment(
    public_code: str,
    body: PaymentCreateIn,
    session: AsyncSession = Depends(db_session),
):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
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
async def lookup_booking(body: BookingLookupIn, session: AsyncSession = Depends(db_session)):
    reservation = await ReservationService(session).lookup(body.phone, body.public_code)
    return reservation_to_out(reservation)


@router.get("/tickets/{public_id}", response_model=TicketOut)
async def get_ticket(public_id: str, session: AsyncSession = Depends(db_session)):
    ticket = await TicketService(session).get_by_public_id(public_id)
    return ticket_to_out(ticket)


@router.post("/tickets/verify", response_model=TicketOut, summary="Verify QR token and mark ticket used")
async def verify_ticket(body: TicketVerifyIn, session: AsyncSession = Depends(db_session)):
    ticket = await TicketService(session).verify_qr(body.qr_token)
    return ticket_to_out(ticket)


@router.get("/reservations/{public_code}/tickets", response_model=list[TicketOut])
async def reservation_tickets(public_code: str, session: AsyncSession = Depends(db_session)):
    service = ReservationService(session)
    reservation = await service.get_by_public_code(public_code)
    tickets = await TicketService(session).list_for_reservation(reservation.id)
    return [ticket_to_out(t) for t in tickets]
