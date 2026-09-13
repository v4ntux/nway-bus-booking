from datetime import datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import (
    ACTIVE_RESERVATION_STATUSES,
    Bus,
    City,
    Payment,
    Reservation,
    ReservationPassenger,
    ReservationSeat,
    ReservationStatus,
    Route,
    TransportCompany,
    Trip,
    User,
    UserRole,
)
from app.repositories.base import apply_company_scope, paginate_params
from app.utils.time import utcnow


class AdminCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def assert_company(self, actor: User, company_id: UUID) -> None:
        if actor.role == UserRole.superadmin:
            return
        if actor.company_id != company_id:
            raise ForbiddenError("COMPANY_SCOPE", "Not allowed for this company")


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def stats(self, actor: User) -> dict:
        today = utcnow().date()
        day_start = datetime.combine(today, time.min).replace(tzinfo=utcnow().tzinfo)
        day_end = day_start + timedelta(days=1)

        trips_stmt = select(func.count()).select_from(Trip).where(
            Trip.departure_datetime >= day_start,
            Trip.departure_datetime < day_end,
        )
        trips_stmt = apply_company_scope(trips_stmt, Trip, actor.role, actor.company_id)
        trips_today = int((await self.session.execute(trips_stmt)).scalar_one())

        passengers_stmt = (
            select(func.count())
            .select_from(ReservationPassenger)
            .join(Reservation, Reservation.id == ReservationPassenger.reservation_id)
            .join(Trip, Trip.id == Reservation.trip_id)
            .where(
                Trip.departure_datetime >= day_start,
                Trip.departure_datetime < day_end,
                Reservation.status == ReservationStatus.confirmed,
            )
        )
        if actor.role != UserRole.superadmin:
            passengers_stmt = passengers_stmt.where(Reservation.company_id == actor.company_id)
        passengers_today = int((await self.session.execute(passengers_stmt)).scalar_one())

        sold_stmt = (
            select(func.count())
            .select_from(ReservationSeat)
            .join(Reservation, Reservation.id == ReservationSeat.reservation_id)
            .join(Trip, Trip.id == Reservation.trip_id)
            .where(
                Trip.departure_datetime >= day_start,
                Trip.departure_datetime < day_end,
                ReservationSeat.is_active_hold.is_(True),
            )
        )
        if actor.role != UserRole.superadmin:
            sold_stmt = sold_stmt.where(Reservation.company_id == actor.company_id)
        sold_seats = int((await self.session.execute(sold_stmt)).scalar_one())

        pending_stmt = select(func.count()).select_from(Reservation).where(
            Reservation.status == ReservationStatus.awaiting_admin_approval
        )
        pending_stmt = apply_company_scope(pending_stmt, Reservation, actor.role, actor.company_id)
        pending_approvals = int((await self.session.execute(pending_stmt)).scalar_one())

        unpaid_stmt = select(func.count()).select_from(Reservation).where(
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.status != ReservationStatus.confirmed,
        )
        unpaid_stmt = apply_company_scope(unpaid_stmt, Reservation, actor.role, actor.company_id)
        unpaid = int((await self.session.execute(unpaid_stmt)).scalar_one())

        large_stmt = select(func.count()).select_from(Reservation).where(
            Reservation.status.in_(
                {ReservationStatus.awaiting_admin_approval, ReservationStatus.awaiting_deposit}
            )
        )
        large_stmt = apply_company_scope(large_stmt, Reservation, actor.role, actor.company_id)
        large_bookings = int((await self.session.execute(large_stmt)).scalar_one())

        bus_capacity_stmt = (
            select(func.coalesce(func.sum(Bus.seat_count), 0))
            .select_from(Trip)
            .join(Bus, Bus.id == Trip.bus_id)
            .where(Trip.departure_datetime >= day_start, Trip.departure_datetime < day_end)
        )
        bus_capacity_stmt = apply_company_scope(bus_capacity_stmt, Trip, actor.role, actor.company_id)
        capacity = int((await self.session.execute(bus_capacity_stmt)).scalar_one())
        free_seats = max(capacity - sold_seats, 0)

        return {
            "trips_today": trips_today,
            "passengers_today": passengers_today,
            "sold_seats": sold_seats,
            "free_seats": free_seats,
            "pending_approvals": pending_approvals,
            "unpaid": unpaid,
            "large_bookings": large_bookings,
        }


class AdminListService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reservations(
        self,
        actor: User,
        *,
        page: int,
        page_size: int,
        trip_id: UUID | None = None,
        status: ReservationStatus | None = None,
        phone: str | None = None,
        public_code: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        page, page_size = paginate_params(page, page_size)
        # reservation_to_out touches seat numbers and payments, so both have to
        # arrive with the row. Lazy-loading either one raises MissingGreenlet.
        stmt = select(Reservation).options(
            selectinload(Reservation.seats).selectinload(ReservationSeat.seat),
            selectinload(Reservation.passengers),
            selectinload(Reservation.payments),
            selectinload(Reservation.trip),
        )
        stmt = apply_company_scope(stmt, Reservation, actor.role, actor.company_id)
        if trip_id:
            stmt = stmt.where(Reservation.trip_id == trip_id)
        if status:
            stmt = stmt.where(Reservation.status == status)
        if phone:
            stmt = stmt.where(Reservation.contact_phone == phone)
        if public_code:
            stmt = stmt.where(Reservation.public_code == public_code.strip().upper())
        if date_from:
            stmt = stmt.where(Reservation.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Reservation.created_at <= date_to)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        rows = (
            await self.session.execute(
                stmt.order_by(Reservation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return {"items": rows, "page": page, "page_size": page_size, "total": total}

    async def payments(self, actor: User, page: int, page_size: int) -> dict:
        page, page_size = paginate_params(page, page_size)
        stmt = select(Payment).options(selectinload(Payment.reservation)).order_by(Payment.created_at.desc())
        if actor.role != UserRole.superadmin:
            stmt = stmt.join(Reservation, Reservation.id == Payment.reservation_id).where(
                Reservation.company_id == actor.company_id
            )
        count_base = select(Payment)
        if actor.role != UserRole.superadmin:
            count_base = count_base.join(Reservation, Reservation.id == Payment.reservation_id).where(
                Reservation.company_id == actor.company_id
            )
        total = int((await self.session.execute(select(func.count()).select_from(count_base.subquery()))).scalar_one())
        items = (
            await self.session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        ).scalars().all()
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    async def passengers(self, actor: User, page: int, page_size: int) -> dict:
        page, page_size = paginate_params(page, page_size)
        stmt = select(ReservationPassenger).join(
            Reservation, Reservation.id == ReservationPassenger.reservation_id
        )
        stmt = apply_company_scope(stmt, Reservation, actor.role, actor.company_id)
        total = int((await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
        items = (
            await self.session.execute(
                stmt.options(selectinload(ReservationPassenger.seat))
                .order_by(ReservationPassenger.first_name)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    async def users(self, actor: User, page: int, page_size: int) -> dict:
        page, page_size = paginate_params(page, page_size)
        stmt = select(User)
        if actor.role != UserRole.superadmin:
            stmt = stmt.where(User.company_id == actor.company_id)
        total = int((await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
        items = (
            await self.session.execute(
                stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    async def companies(self, actor: User, page: int, page_size: int) -> dict:
        page, page_size = paginate_params(page, page_size)
        stmt = select(TransportCompany)
        if actor.role != UserRole.superadmin:
            stmt = stmt.where(TransportCompany.id == actor.company_id)
        total = int((await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
        items = (
            await self.session.execute(
                stmt.order_by(TransportCompany.name).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return {"items": items, "page": page, "page_size": page_size, "total": total}
