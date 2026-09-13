from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.exceptions import DomainError
from app.models import PaymentMethod, Reservation, ReservationStatus, Ticket, TicketStatus, Trip, TripStatus
from app.services.payment import PaymentService
from app.services.reservation import PassengerInput, ReservationService
from app.utils.time import utcnow


def _passengers(seats, names):
    return [
        PassengerInput(seat_id=seat.id, first_name=name)
        for seat, name in zip(seats, names, strict=True)
    ]


async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_free_seat_is_bookable(world):
    session = world["session"]
    trip = world["trip"]
    seat = world["seats"][0]
    service = ReservationService(session)
    reservation = await service.create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    assert reservation.status == ReservationStatus.pending
    assert reservation.public_code
    assert "-" in reservation.public_code
    assert reservation.seats[0].price_minor == trip.base_price_minor


async def test_cannot_double_book_same_seat(world):
    session = world["session"]
    trip = world["trip"]
    seat = world["seats"][0]
    service = ReservationService(session)
    await service.create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    with pytest.raises(DomainError) as exc:
        await service.create(
            trip_id=trip.id,
            seat_ids=[seat.id],
            contact_phone="+998901111111",
            passengers=_passengers([seat], ["Bob"]),
            user_id=None,
        )
    assert exc.value.code == "SEAT_ALREADY_RESERVED"


async def test_cancel_frees_seat(world):
    session = world["session"]
    trip = world["trip"]
    seat = world["seats"][0]
    service = ReservationService(session)
    first = await service.create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    await service.cancel(first.id, actor_id=None)
    second = await service.create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998907777777",
        passengers=_passengers([seat], ["Bob"]),
        user_id=None,
    )
    assert second.status == ReservationStatus.pending


async def test_expire_frees_seat(world):
    session = world["session"]
    trip = world["trip"]
    seat = world["seats"][0]
    service = ReservationService(session)
    first = await service.create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    first.expires_at = utcnow() - timedelta(minutes=1)
    await session.commit()
    count = await service.expire_pending_reservations()
    assert count >= 1
    second = await service.create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998907777777",
        passengers=_passengers([seat], ["Bob"]),
        user_id=None,
    )
    assert second.id != first.id


async def test_multi_seat_booking(world):
    session = world["session"]
    trip = world["trip"]
    seats = world["seats"][:2]
    reservation = await ReservationService(session).create(
        trip_id=trip.id,
        seat_ids=[s.id for s in seats],
        contact_phone="+998901234567",
        passengers=_passengers(seats, ["Ali", "Vali"]),
        user_id=None,
    )
    assert len(reservation.seats) == 2
    assert reservation.total_amount_minor == trip.base_price_minor * 2


async def test_multi_seat_rolls_back_on_conflict(world):
    session = world["session"]
    trip = world["trip"]
    service = ReservationService(session)
    await service.create(
        trip_id=trip.id,
        seat_ids=[world["seats"][1].id],
        contact_phone="+998901234567",
        passengers=_passengers([world["seats"][1]], ["Held"]),
        user_id=None,
    )
    with pytest.raises(DomainError) as exc:
        await service.create(
            trip_id=trip.id,
            seat_ids=[world["seats"][0].id, world["seats"][1].id],
            contact_phone="+998909000000",
            passengers=_passengers(world["seats"][:2], ["A", "B"]),
            user_id=None,
        )
    assert exc.value.code == "SEAT_ALREADY_RESERVED"
    leftover = (
        await session.execute(
            select(Reservation).where(Reservation.contact_phone == "+998909000000")
        )
    ).scalar_one_or_none()
    assert leftover is None


async def test_large_booking_awaits_admin(world):
    session = world["session"]
    trip = world["trip"]
    seats = world["seats"][:4]
    reservation = await ReservationService(session).create(
        trip_id=trip.id,
        seat_ids=[s.id for s in seats],
        contact_phone="+998901234567",
        passengers=_passengers(seats, ["A", "B", "C", "D"]),
        user_id=None,
    )
    assert reservation.status == ReservationStatus.awaiting_admin_approval


async def test_payment_success_confirms_and_issues_tickets(world, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "ALLOW_MOCK_PAYMENTS", True)
    session = world["session"]
    trip = world["trip"]
    seat = world["seats"][0]
    reservation = await ReservationService(session).create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    payments = PaymentService(session)
    payment = await payments.create_for_reservation(reservation.id, PaymentMethod.online)
    paid = await payments.mock_success(payment.id)
    assert paid.status.value == "paid"
    confirmed = await ReservationService(session).get_by_id(reservation.id)
    assert confirmed.status == ReservationStatus.confirmed
    tickets = (await session.execute(select(Ticket).where(Ticket.reservation_id == reservation.id))).scalars().all()
    assert len(tickets) == 1
    assert tickets[0].status == TicketStatus.valid


async def test_failed_payment_does_not_confirm(world, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "ALLOW_MOCK_PAYMENTS", True)
    session = world["session"]
    trip = world["trip"]
    seat = world["seats"][0]
    reservation = await ReservationService(session).create(
        trip_id=trip.id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    payments = PaymentService(session)
    payment = await payments.create_for_reservation(reservation.id, PaymentMethod.online)
    failed = await payments.mock_fail(payment.id)
    assert failed.status.value == "failed"
    current = await ReservationService(session).get_by_id(reservation.id)
    assert current.status == ReservationStatus.pending


async def test_cannot_book_zero_seats(world):
    session = world["session"]
    with pytest.raises(DomainError) as exc:
        await ReservationService(session).create(
            trip_id=world["trip"].id,
            seat_ids=[],
            contact_phone="+998901234567",
            passengers=[],
            user_id=None,
        )
    assert exc.value.code == "NO_SEATS"


async def test_cannot_book_cancelled_trip(world):
    session = world["session"]
    trip = await session.get(Trip, world["trip"].id)
    trip.status = TripStatus.cancelled
    await session.commit()
    seat = world["seats"][0]
    with pytest.raises(DomainError) as exc:
        await ReservationService(session).create(
            trip_id=trip.id,
            seat_ids=[seat.id],
            contact_phone="+998901234567",
            passengers=_passengers([seat], ["Ali"]),
            user_id=None,
        )
    assert exc.value.code == "TRIP_NOT_BOOKABLE"


async def test_confirming_expired_forbidden(world):
    session = world["session"]
    seat = world["seats"][0]
    service = ReservationService(session)
    reservation = await service.create(
        trip_id=world["trip"].id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    reservation.expires_at = utcnow() - timedelta(minutes=5)
    await session.commit()
    with pytest.raises(DomainError) as exc:
        await service.confirm(reservation.id, actor_id=None)
    assert exc.value.code == "RESERVATION_EXPIRED"


async def test_lookup_and_error_envelope(client: AsyncClient, world):
    session = world["session"]
    seat = world["seats"][0]
    reservation = await ReservationService(session).create(
        trip_id=world["trip"].id,
        seat_ids=[seat.id],
        contact_phone="+998901234567",
        passengers=_passengers([seat], ["Ali"]),
        user_id=None,
    )
    response = await client.post(
        "/api/v1/bookings/lookup",
        json={"phone": "+998901234567", "public_code": reservation.public_code},
    )
    assert response.status_code == 200
    assert response.json()["public_code"] == reservation.public_code

    conflict = await client.post(
        "/api/v1/reservations",
        json={
            "trip_id": str(world["trip"].id),
            "seat_ids": [str(seat.id)],
            "contact_phone": "+998901111111",
            "passengers": [{"seat_id": str(seat.id), "first_name": "Bob"}],
        },
    )
    assert conflict.status_code == 409
    body = conflict.json()
    assert body["error"]["code"] == "SEAT_ALREADY_RESERVED"
