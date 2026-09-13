from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import DomainError, NotFoundError
from app.models import (
    ACTIVE_RESERVATION_STATUSES,
    BOOKABLE_TRIP_STATUSES,
    Bus,
    City,
    Reservation,
    ReservationSeat,
    Route,
    Seat,
    Trip,
    TripStatus,
)
from app.services.audit import count_held_seats, write_audit
from app.utils.time import utcnow


class TripService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def search(self, origin_city_id: UUID, destination_city_id: UUID, travel_date: date) -> list[dict]:
        held = (
            select(ReservationSeat.trip_id, func.count().label("held"))
            .where(ReservationSeat.is_active_hold.is_(True))
            .group_by(ReservationSeat.trip_id)
            .subquery()
        )
        origin = await self.session.get(City, origin_city_id)
        dest = await self.session.get(City, destination_city_id)
        if origin is None or dest is None:
            raise NotFoundError("CITY_NOT_FOUND", "City not found")
        day_start = datetime.combine(travel_date, time.min, tzinfo=ZoneInfo(origin.timezone))
        day_end = day_start + timedelta(days=1)
        stmt = (
            select(Trip, Bus, Route, City, held.c.held)
            .join(Bus, Bus.id == Trip.bus_id)
            .join(Route, Route.id == Trip.route_id)
            .join(City, City.id == Route.origin_city_id)
            .outerjoin(held, held.c.trip_id == Trip.id)
            .options(
                selectinload(Trip.route).selectinload(Route.origin_city),
                selectinload(Trip.route).selectinload(Route.destination_city),
                selectinload(Trip.bus),
            )
            .where(
                Route.origin_city_id == origin_city_id,
                Route.destination_city_id == destination_city_id,
                Trip.departure_datetime >= day_start,
                Trip.departure_datetime < day_end,
                Trip.departure_datetime > utcnow(),
                Trip.status.in_(BOOKABLE_TRIP_STATUSES),
                Route.active.is_(True),
            )
            .order_by(Trip.departure_datetime)
        )
        result = await self.session.execute(stmt)
        rows = []
        for trip, bus, route, _origin_city, held_count in result.all():
            held_n = int(held_count or 0)
            bookable_seats = await self._bookable_seat_count(bus.id)
            rows.append(
                {
                    "trip": trip,
                    "available_seats": max(bookable_seats - held_n, 0),
                    "bus": bus,
                    "route": route,
                }
            )
        return rows

    async def _bookable_seat_count(self, bus_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Seat)
            .where(
                Seat.bus_id == bus_id,
                Seat.active.is_(True),
                Seat.is_blocked.is_(False),
            )
        )
        return int(result.scalar_one())

    async def get(self, trip_id: UUID) -> Trip:
        result = await self.session.execute(
            select(Trip)
            .options(
                selectinload(Trip.route).selectinload(Route.origin_city),
                selectinload(Trip.route).selectinload(Route.destination_city),
                selectinload(Trip.bus).selectinload(Bus.layout),
            )
            .where(Trip.id == trip_id)
        )
        trip = result.scalar_one_or_none()
        if trip is None:
            raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
        return trip

    async def available_seats_count(self, trip: Trip) -> int:
        bookable = await self._bookable_seat_count(trip.bus_id)
        held = await count_held_seats(self.session, trip.id)
        return max(bookable - held, 0)

    async def create(
        self,
        *,
        route_id: UUID,
        bus_id: UUID,
        company_id: UUID,
        departure_datetime: datetime,
        base_price_minor: int,
        currency: str,
        boarding_location: str | None,
        destination_location: str | None,
        driver_id: UUID | None,
        actor_id: UUID | None,
        status: TripStatus = TripStatus.scheduled,
    ) -> Trip:
        if base_price_minor < 0:
            raise DomainError("INVALID_PRICE", "Price cannot be negative")
        bus = await self.session.get(Bus, bus_id)
        if bus is None or not bus.active:
            raise DomainError("BUS_REQUIRED", "Trip cannot be created without an active bus")
        if bus.company_id != company_id:
            raise DomainError("BUS_COMPANY_MISMATCH", "Bus does not belong to this company")
        route = await self.session.get(Route, route_id)
        if route is None or not route.active:
            raise NotFoundError("ROUTE_NOT_FOUND", "Route not found")
        if route.company_id != company_id:
            raise DomainError("ROUTE_COMPANY_MISMATCH", "Route does not belong to this company")
        arrival = departure_datetime + timedelta(minutes=route.estimated_duration_minutes)
        trip = Trip(
            route_id=route_id,
            bus_id=bus_id,
            company_id=company_id,
            driver_id=driver_id,
            departure_datetime=departure_datetime,
            estimated_arrival_datetime=arrival,
            status=status,
            base_price_minor=base_price_minor,
            currency=currency,
            boarding_location=boarding_location,
            destination_location=destination_location,
        )
        self.session.add(trip)
        await self.session.flush()
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="trip.create",
            entity_type="trip",
            entity_id=trip.id,
            after={"bus_id": str(bus_id), "route_id": str(route_id)},
        )
        await self.session.commit()
        return await self.get(trip.id)

    async def change_bus(self, trip_id: UUID, new_bus_id: UUID, actor_id: UUID | None) -> Trip:
        trip = await self.session.get(Trip, trip_id)
        if trip is None:
            raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
        held = await count_held_seats(self.session, trip.id)
        if held > 0:
            raise DomainError(
                "BUS_CHANGE_FORBIDDEN",
                "Cannot change bus while active reservations exist",
                status_code=409,
            )
        bus = await self.session.get(Bus, new_bus_id)
        if bus is None or bus.company_id != trip.company_id:
            raise DomainError("BUS_COMPANY_MISMATCH", "Bus does not belong to this company")
        before = {"bus_id": str(trip.bus_id)}
        trip.bus_id = new_bus_id
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="trip.change_bus",
            entity_type="trip",
            entity_id=trip.id,
            before=before,
            after={"bus_id": str(new_bus_id)},
        )
        await self.session.commit()
        return await self.get(trip.id)

    async def cancel_trip(self, trip_id: UUID, actor_id: UUID | None) -> Trip:
        trip = await self.session.get(Trip, trip_id)
        if trip is None:
            raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
        trip.status = TripStatus.cancelled
        result = await self.session.execute(
            select(Reservation).where(
                Reservation.trip_id == trip_id,
                Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            )
        )
        from app.models.enums import ReservationStatus, TicketStatus
        from app.models.ticket import Ticket

        for reservation in result.scalars().all():
            reservation.status = ReservationStatus.cancelled
            for seat in (
                await self.session.execute(
                    select(ReservationSeat).where(ReservationSeat.reservation_id == reservation.id)
                )
            ).scalars().all():
                seat.is_active_hold = False
            tickets = (
                await self.session.execute(select(Ticket).where(Ticket.reservation_id == reservation.id))
            ).scalars().all()
            for ticket in tickets:
                ticket.status = TicketStatus.cancelled
            await write_audit(
                self.session,
                actor_id=actor_id,
                action="reservation.cancel_trip",
                entity_type="reservation",
                entity_id=reservation.id,
                after={"reason": "trip_cancelled"},
            )
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="trip.cancel",
            entity_type="trip",
            entity_id=trip.id,
        )
        await self.session.commit()
        return await self.get(trip.id)
