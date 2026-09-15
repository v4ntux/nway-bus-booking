from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.core.rate_limit import rate_limiter
from app.models import (
    ACTIVE_RESERVATION_STATUSES,
    BOOKABLE_TRIP_STATUSES,
    Bus,
    BusLayout,
    LayoutCell,
    PaymentMethod,
    PaymentStatus,
    Reservation,
    ReservationPassenger,
    ReservationSeat,
    ReservationStatus,
    Seat,
    Ticket,
    TicketStatus,
    Trip,
    User,
    UserRole,
    UserStats,
    UserStatus,
)
from app.services.audit import write_audit
from app.models.telegram import TelegramDelivery
from app.utils.codes import generate_booking_code, generate_qr_token, generate_ticket_public_id
from app.utils.phone import normalize_phone
from app.utils.time import utcnow

ALLOWED_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.pending: {
        ReservationStatus.confirmed,
        ReservationStatus.cancelled,
        ReservationStatus.expired,
        ReservationStatus.awaiting_deposit,
        ReservationStatus.awaiting_admin_approval,
    },
    ReservationStatus.awaiting_admin_approval: {
        ReservationStatus.confirmed,
        ReservationStatus.awaiting_deposit,
        ReservationStatus.cancelled,
        ReservationStatus.expired,
    },
    ReservationStatus.awaiting_deposit: {
        ReservationStatus.awaiting_admin_approval,
        ReservationStatus.confirmed,
        ReservationStatus.cancelled,
        ReservationStatus.expired,
    },
    ReservationStatus.confirmed: {
        ReservationStatus.cancelled,
        ReservationStatus.completed,
        ReservationStatus.no_show,
    },
    ReservationStatus.cancelled: set(),
    ReservationStatus.expired: set(),
    ReservationStatus.completed: set(),
    ReservationStatus.no_show: set(),
}


async def queue_telegram_tickets(session: AsyncSession, reservation_id: UUID, chat_id: int, *, resend: bool = False) -> None:
    """Queue PNG delivery of every valid ticket; the caller commits. `resend` resets sent ones."""
    tickets = await session.scalars(select(Ticket).where(
        Ticket.reservation_id == reservation_id, Ticket.status == TicketStatus.valid))
    for ticket in tickets:
        stmt = insert(TelegramDelivery).values(ticket_id=ticket.id, chat_id=chat_id, attempts=0)
        if resend:
            stmt = stmt.on_conflict_do_update(index_elements=[TelegramDelivery.ticket_id], set_={
                "sent_at": None, "attempts": 0, "available_at": utcnow(), "last_error": None})
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=[TelegramDelivery.ticket_id])
        await session.execute(stmt)


@dataclass
class PassengerInput:
    seat_id: UUID
    first_name: str
    last_name: str | None = None
    phone: str | None = None
    document_type: str | None = None
    document_number: str | None = None


class ReservationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    def _transition(self, reservation: Reservation, target: ReservationStatus) -> None:
        allowed = ALLOWED_TRANSITIONS.get(reservation.status, set())
        if target not in allowed:
            raise DomainError(
                "INVALID_STATUS_TRANSITION",
                f"Cannot change reservation from {reservation.status.value} to {target.value}",
                status_code=409,
            )
        reservation.status = target

    async def create(
        self,
        *,
        trip_id: UUID,
        seat_ids: list[UUID],
        contact_phone: str,
        passengers: list[PassengerInput],
        user_id: UUID | None,
        booking_request_key: str | None = None,
        telegram_chat_id: int | None = None,
    ) -> Reservation:
        if booking_request_key:
            existing = await self.session.scalar(
                select(Reservation).where(Reservation.booking_request_key == booking_request_key)
            )
            if existing:
                if existing.telegram_chat_id != telegram_chat_id:
                    raise DomainError("BOOKING_OWNER_MISMATCH", "Booking belongs to another user", 403)
                return await self.get_by_id(existing.id)
        if not seat_ids:
            raise DomainError("NO_SEATS", "At least one seat is required")
        if len(seat_ids) != len(set(seat_ids)):
            raise DomainError("DUPLICATE_SEATS", "Duplicate seats in request")
        if len(passengers) != len(seat_ids):
            raise DomainError("PASSENGER_SEAT_MISMATCH", "Each seat needs a passenger")
        passenger_seats = {p.seat_id for p in passengers}
        if passenger_seats != set(seat_ids):
            raise DomainError("PASSENGER_SEAT_MISMATCH", "Passenger seats must match selected seats")

        phone = normalize_phone(contact_phone)
        await rate_limiter.check(f"reservation:{phone}", limit=20, window_seconds=3600)

        trip = (
            await self.session.execute(select(Trip).where(Trip.id == trip_id).with_for_update())
        ).scalar_one_or_none()
        if trip is None:
            raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
        if trip.status not in BOOKABLE_TRIP_STATUSES:
            raise DomainError("TRIP_NOT_BOOKABLE", "This trip cannot be booked", status_code=409)
        if trip.departure_datetime <= utcnow():
            raise DomainError("TRIP_DEPARTED", "This trip has already departed", status_code=409)

        seats_result = await self.session.execute(
            select(Seat).where(Seat.id.in_(seat_ids)).with_for_update()
        )
        seats = list(seats_result.scalars().all())
        if len(seats) != len(seat_ids):
            raise NotFoundError("SEAT_NOT_FOUND", "One or more seats were not found")
        for seat in seats:
            if seat.bus_id != trip.bus_id:
                raise DomainError("SEAT_WRONG_BUS", "Seat does not belong to this trip's bus")
            if not seat.active or seat.is_blocked or seat.type.value == "blocked":
                raise DomainError("SEAT_NOT_BOOKABLE", f"Seat {seat.seat_number} cannot be booked")

        held = (
            await self.session.execute(
                select(ReservationSeat.seat_id).where(
                    ReservationSeat.trip_id == trip.id,
                    ReservationSeat.seat_id.in_(seat_ids),
                    ReservationSeat.is_active_hold.is_(True),
                )
            )
        ).scalars().all()
        if held:
            raise ConflictError("SEAT_ALREADY_RESERVED", "One or more seats are already reserved")

        user = await self._get_or_create_user(phone, user_id)
        now = utcnow()
        seat_count = len(seats)
        status = (
            ReservationStatus.awaiting_admin_approval
            if seat_count >= self.settings.LARGE_BOOKING_THRESHOLD
            else ReservationStatus.pending
        )
        expires_at = now + timedelta(minutes=self.settings.BOOKING_HOLD_MINUTES)
        if status == ReservationStatus.awaiting_admin_approval:
            expires_at = trip.departure_datetime - timedelta(
                minutes=self.settings.OFFLINE_BOOKING_DEADLINE_MINUTES
            )

        public_code = await self._unique_booking_code()
        total = trip.base_price_minor * seat_count
        reservation = Reservation(
            user_id=user.id,
            trip_id=trip.id,
            company_id=trip.company_id,
            public_code=public_code,
            status=status,
            payment_status=PaymentStatus.unpaid,
            total_amount_minor=total,
            currency=trip.currency,
            expires_at=expires_at,
            contact_phone=phone,
            booking_request_key=booking_request_key,
            telegram_chat_id=telegram_chat_id,
        )
        self.session.add(reservation)
        await self.session.flush()

        by_id = {s.id: s for s in seats}
        for passenger in passengers:
            seat = by_id[passenger.seat_id]
            self.session.add(
                ReservationSeat(
                    reservation_id=reservation.id,
                    trip_id=trip.id,
                    seat_id=seat.id,
                    price_minor=trip.base_price_minor,
                    is_active_hold=True,
                )
            )
            p_phone = normalize_phone(passenger.phone) if passenger.phone else None
            self.session.add(
                ReservationPassenger(
                    reservation_id=reservation.id,
                    seat_id=seat.id,
                    first_name=passenger.first_name.strip(),
                    last_name=passenger.last_name.strip() if passenger.last_name else None,
                    phone=p_phone,
                    document_type=passenger.document_type,
                    document_number=passenger.document_number,
                )
            )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("SEAT_ALREADY_RESERVED", "One or more seats are already reserved") from exc

        await write_audit(
            self.session,
            actor_id=user.id,
            action="reservation.create",
            entity_type="reservation",
            entity_id=reservation.id,
            after={"seats": [str(s) for s in seat_ids], "status": status.value},
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def choose_pay_later(self, reservation_id: UUID, method: PaymentMethod) -> Reservation:
        reservation = await self._lock(reservation_id)
        if reservation.status != ReservationStatus.pending:
            raise DomainError("INVALID_STATUS_TRANSITION", "Pay later is only available for pending bookings")
        if method not in {PaymentMethod.cash, PaymentMethod.transfer, PaymentMethod.other}:
            raise DomainError("INVALID_PAYMENT_METHOD", "Invalid offline payment method")
        trip = await self.session.get(Trip, reservation.trip_id)
        assert trip is not None
        reservation.payment_method = method
        reservation.expires_at = trip.departure_datetime - timedelta(
            minutes=self.settings.OFFLINE_BOOKING_DEADLINE_MINUTES
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def confirm(self, reservation_id: UUID, actor_id: UUID | None) -> Reservation:
        reservation = await self._lock(reservation_id)
        if reservation.expires_at and reservation.expires_at < utcnow() and reservation.status != ReservationStatus.confirmed:
            raise DomainError("RESERVATION_EXPIRED", "Cannot confirm an expired reservation", status_code=409)
        if reservation.status == ReservationStatus.awaiting_deposit and not reservation.deposit_received:
            raise DomainError("DEPOSIT_REQUIRED", "Deposit must be received before confirmation")
        self._transition(reservation, ReservationStatus.confirmed)
        reservation.expires_at = None
        await self._issue_tickets(reservation)
        await self.session.flush()
        if reservation.telegram_chat_id:
            await queue_telegram_tickets(self.session, reservation.id, reservation.telegram_chat_id)
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="reservation.confirm",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def confirm_cash(self, reservation_id: UUID) -> Reservation:
        reservation = await self._lock(reservation_id)
        if reservation.status == ReservationStatus.confirmed:
            return await self.get_by_id(reservation.id)
        if reservation.status not in {ReservationStatus.pending, ReservationStatus.awaiting_admin_approval}:
            raise DomainError("INVALID_STATUS_TRANSITION", "Bu bronni tasdiqlab bo‘lmaydi.", 409)
        trip = await self.session.get(Trip, reservation.trip_id)
        if trip.departure_datetime <= utcnow() or (reservation.expires_at and reservation.expires_at <= utcnow()):
            raise DomainError("RESERVATION_EXPIRED", "Bron muddati tugadi. Reysni qaytadan tanlang.", 409)
        reservation.payment_method = PaymentMethod.cash
        await self.session.flush()
        if reservation.status == ReservationStatus.awaiting_admin_approval:
            await self.session.commit()
            return await self.get_by_id(reservation.id)
        return await self.confirm(reservation.id, actor_id=None)

    async def cancel(self, reservation_id: UUID, actor_id: UUID | None) -> Reservation:
        reservation = await self._lock(reservation_id)
        self._transition(reservation, ReservationStatus.cancelled)
        await self._release_seats(reservation)
        await self._cancel_tickets(reservation)
        stats = (
            await self.session.execute(select(UserStats).where(UserStats.user_id == reservation.user_id))
        ).scalar_one_or_none()
        if stats:
            stats.cancelled_reservations += 1
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="reservation.cancel",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def expire(self, reservation_id: UUID) -> Reservation:
        reservation = await self._lock(reservation_id)
        self._transition(reservation, ReservationStatus.expired)
        await self._release_seats(reservation)
        await write_audit(
            self.session,
            actor_id=None,
            action="reservation.expire",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def mark_no_show(self, reservation_id: UUID, actor_id: UUID | None) -> Reservation:
        reservation = await self._lock(reservation_id)
        self._transition(reservation, ReservationStatus.no_show)
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="reservation.no_show",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def require_deposit(self, reservation_id: UUID, actor_id: UUID | None) -> Reservation:
        reservation = await self._lock(reservation_id)
        self._transition(reservation, ReservationStatus.awaiting_deposit)
        reservation.deposit_required = True
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="reservation.require_deposit",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def reject(self, reservation_id: UUID, actor_id: UUID | None) -> Reservation:
        reservation = await self._lock(reservation_id)
        if reservation.status not in {
            ReservationStatus.awaiting_admin_approval,
            ReservationStatus.awaiting_deposit,
            ReservationStatus.pending,
        }:
            raise DomainError("INVALID_STATUS_TRANSITION", "Reservation cannot be rejected")
        self._transition(reservation, ReservationStatus.cancelled)
        await self._release_seats(reservation)
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="reservation.reject",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def mark_deposit_received(self, reservation_id: UUID, actor_id: UUID | None) -> Reservation:
        reservation = await self._lock(reservation_id)
        if reservation.status != ReservationStatus.awaiting_deposit:
            raise DomainError("INVALID_STATUS_TRANSITION", "Reservation is not awaiting a deposit")
        reservation.deposit_received = True
        reservation.payment_status = PaymentStatus.partially_paid
        self._transition(reservation, ReservationStatus.awaiting_admin_approval)
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="reservation.deposit_received",
            entity_type="reservation",
            entity_id=reservation.id,
        )
        await self.session.commit()
        return await self.get_by_id(reservation.id)

    async def lookup(self, phone_raw: str, public_code: str) -> Reservation:
        phone = normalize_phone(phone_raw)
        await rate_limiter.check(f"lookup:{phone}", limit=30, window_seconds=3600)
        code = public_code.strip().upper()
        result = await self.session.execute(
            select(Reservation).where(
                Reservation.public_code == code,
                Reservation.contact_phone == phone,
            )
        )
        reservation = result.scalar_one_or_none()
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        return await self.get_by_id(reservation.id)

    async def get_by_public_code(self, public_code: str) -> Reservation:
        result = await self.session.execute(
            select(Reservation).where(Reservation.public_code == public_code.strip().upper())
        )
        reservation = result.scalar_one_or_none()
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        return await self.get_by_id(reservation.id)

    async def get_by_id(self, reservation_id: UUID) -> Reservation:
        result = await self.session.execute(
            select(Reservation)
            .options(
                selectinload(Reservation.seats).selectinload(ReservationSeat.seat),
                selectinload(Reservation.passengers).selectinload(ReservationPassenger.seat),
                selectinload(Reservation.payments),
                selectinload(Reservation.trip).selectinload(Trip.route),
                selectinload(Reservation.trip).selectinload(Trip.bus),
            )
            .where(Reservation.id == reservation_id)
        )
        reservation = result.scalar_one_or_none()
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        return reservation

    async def expire_pending_reservations(self) -> int:
        now = utcnow()
        hold_result = await self.session.execute(
            select(Reservation.id).where(
                Reservation.status.in_(
                    {
                        ReservationStatus.pending,
                        ReservationStatus.awaiting_deposit,
                        ReservationStatus.awaiting_admin_approval,
                    }
                ),
                Reservation.expires_at.is_not(None),
                Reservation.expires_at <= now,
            )
        )
        expired_ids = [row[0] for row in hold_result.all()]

        deadline_delta = timedelta(minutes=self.settings.OFFLINE_BOOKING_DEADLINE_MINUTES)
        deadline_result = await self.session.execute(
            select(Reservation.id)
            .join(Trip, Trip.id == Reservation.trip_id)
            .where(
                Reservation.status.in_(
                    {
                        ReservationStatus.pending,
                        ReservationStatus.awaiting_deposit,
                        ReservationStatus.awaiting_admin_approval,
                    }
                ),
                Reservation.payment_status.in_({PaymentStatus.unpaid, PaymentStatus.pending, PaymentStatus.failed}),
                Trip.departure_datetime <= now + deadline_delta,
            )
        )
        expired_ids.extend(row[0] for row in deadline_result.all())
        unique_ids = list(dict.fromkeys(expired_ids))
        count = 0
        for reservation_id in unique_ids:
            try:
                await self.expire(reservation_id)
                count += 1
            except DomainError:
                await self.session.rollback()
        return count

    async def _lock(self, reservation_id: UUID) -> Reservation:
        result = await self.session.execute(
            select(Reservation).where(Reservation.id == reservation_id).with_for_update().execution_options(populate_existing=True)
        )
        reservation = result.scalar_one_or_none()
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        return reservation

    async def _release_seats(self, reservation: Reservation) -> None:
        result = await self.session.execute(
            select(ReservationSeat).where(ReservationSeat.reservation_id == reservation.id)
        )
        for seat in result.scalars().all():
            seat.is_active_hold = False

    async def _cancel_tickets(self, reservation: Reservation) -> None:
        result = await self.session.execute(select(Ticket).where(Ticket.reservation_id == reservation.id))
        for ticket in result.scalars().all():
            ticket.status = TicketStatus.cancelled

    async def _issue_tickets(self, reservation: Reservation) -> None:
        existing = (
            await self.session.execute(select(Ticket).where(Ticket.reservation_id == reservation.id))
        ).scalars().all()
        if existing:
            return
        passengers = (
            await self.session.execute(
                select(ReservationPassenger).where(ReservationPassenger.reservation_id == reservation.id)
            )
        ).scalars().all()
        for passenger in passengers:
            self.session.add(
                Ticket(
                    public_id=generate_ticket_public_id(),
                    qr_token=generate_qr_token(),
                    reservation_id=reservation.id,
                    passenger_id=passenger.id,
                    trip_id=reservation.trip_id,
                    seat_id=passenger.seat_id,
                    status=TicketStatus.valid,
                )
            )

    async def _unique_booking_code(self) -> str:
        for _ in range(20):
            code = generate_booking_code()
            exists = (
                await self.session.execute(select(Reservation.id).where(Reservation.public_code == code))
            ).scalar_one_or_none()
            if exists is None:
                return code
        raise DomainError("CODE_GENERATION_FAILED", "Could not generate booking code")

    async def _get_or_create_user(self, phone: str, user_id: UUID | None) -> User:
        if user_id:
            user = await self.session.get(User, user_id)
            if user:
                if user.status == UserStatus.blocked:
                    raise DomainError("USER_BLOCKED", "Account is blocked", status_code=403)
                return user
        result = await self.session.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        if user:
            if user.status == UserStatus.blocked:
                raise DomainError("USER_BLOCKED", "Account is blocked", status_code=403)
            return user
        user = User(phone=phone, role=UserRole.passenger, status=UserStatus.active, phone_verified=False)
        self.session.add(user)
        await self.session.flush()
        self.session.add(UserStats(user_id=user.id))
        return user


class SeatMapService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def trip_seat_map(self, trip_id: UUID) -> dict:
        trip = await self.session.get(Trip, trip_id)
        if trip is None:
            raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
        layout_result = await self.session.execute(
            select(BusLayout)
            .options(selectinload(BusLayout.cells).selectinload(LayoutCell.seat))
            .where(BusLayout.bus_id == trip.bus_id)
        )
        layout = layout_result.scalar_one_or_none()
        held_result = await self.session.execute(
            select(ReservationSeat.seat_id).where(
                ReservationSeat.trip_id == trip_id,
                ReservationSeat.is_active_hold.is_(True),
            )
        )
        held = {row[0] for row in held_result.all()}
        cells = []
        if layout:
            for cell in sorted(layout.cells, key=lambda c: (c.row, c.column)):
                seat_payload = None
                if cell.seat is not None:
                    blocked = (not cell.seat.active) or cell.seat.is_blocked
                    if blocked:
                        status = "blocked"
                    elif cell.seat.id in held:
                        status = "reserved"
                    else:
                        status = "available"
                    seat_payload = {
                        "id": cell.seat.id,
                        "seat_number": cell.seat.seat_number,
                        "type": cell.seat.type.value,
                        "status": status,
                        "is_accessibility": cell.seat.is_accessibility,
                        "is_premium": cell.seat.is_premium,
                        "is_women_only": cell.seat.is_women_only,
                    }
                cells.append(
                    {
                        "row": cell.row,
                        "column": cell.column,
                        "cell_type": cell.cell_type.value,
                        "seat": seat_payload,
                    }
                )
            return {
                "trip_id": trip.id,
                "rows": layout.rows,
                "columns": layout.columns,
                "cells": cells,
            }
        seats = (
            await self.session.execute(select(Seat).where(Seat.bus_id == trip.bus_id))
        ).scalars().all()
        return {
            "trip_id": trip.id,
            "rows": max((s.row for s in seats), default=0) + 1,
            "columns": max((s.column for s in seats), default=0) + 1,
            "cells": [
                {
                    "row": s.row,
                    "column": s.column,
                    "cell_type": "seat",
                    "seat": {
                        "id": s.id,
                        "seat_number": s.seat_number,
                        "type": s.type.value,
                        "status": "blocked"
                        if (not s.active or s.is_blocked)
                        else ("reserved" if s.id in held else "available"),
                        "is_accessibility": s.is_accessibility,
                        "is_premium": s.is_premium,
                        "is_women_only": s.is_women_only,
                    },
                }
                for s in seats
            ],
        }
