from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, StaffUser, db_session
from app.models.faq import FaqItem
from app.schemas.faq import FaqIn, FaqOut
from app.api.serializers import reservation_to_out
from app.core.config import get_settings
from app.core.exceptions import DomainError, ForbiddenError, NotFoundError
from app.models import (
    Bus,
    BusLayout,
    City,
    LayoutCell,
    ReservationSeat,
    ReservationStatus,
    Route,
    RouteStop,
    Seat,
    TransportCompany,
    Trip,
    User,
    UserRole,
)
from app.schemas.booking import (
    CompanyIn,
    CompanyOut,
    DashboardOut,
    PageCompanies,
    PagePassengers,
    PagePayments,
    PageReservations,
    PageUsers,
    PaymentOut,
    ReservationOut,
    UserAdminOut,
)
from app.schemas.catalog import (
    BusIn,
    BusLayoutOut,
    BusOut,
    CityIn,
    CityOut,
    LayoutCellOut,
    LayoutCellPatch,
    LayoutGenerateIn,
    RouteIn,
    RouteOut,
    TripCreateIn,
    TripOut,
    TripBusChangeIn,
    TripPatchIn,
)
from app.services.admin import AdminListService, DashboardService
from app.services.payment import PaymentService
from app.services.reservation import ReservationService
from app.services.seed import build_coach_layout
from app.services.trip import TripService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(StaffUser)])


def _company_id(actor: User, requested: UUID | None) -> UUID:
    if actor.role == UserRole.superadmin:
        if requested:
            return requested
        if actor.company_id:
            return actor.company_id
        raise ForbiddenError("COMPANY_REQUIRED", "company_id is required")
    if not actor.company_id:
        raise ForbiddenError("COMPANY_SCOPE", "User is not assigned to a company")
    if requested and requested != actor.company_id:
        raise ForbiddenError("COMPANY_SCOPE", "Not allowed for this company")
    return actor.company_id


@router.get("/faq", response_model=list[FaqOut])
async def admin_faq(session: AsyncSession = Depends(db_session)):
    result = await session.scalars(select(FaqItem).order_by(FaqItem.lang, FaqItem.position, FaqItem.created_at))
    return [FaqOut.model_validate(item) for item in result.all()]


@router.post("/faq", response_model=FaqOut, status_code=201, dependencies=[Depends(AdminUser)])
async def create_faq(body: FaqIn, session: AsyncSession = Depends(db_session)):
    item = FaqItem(**body.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return FaqOut.model_validate(item)


@router.patch("/faq/{item_id}", response_model=FaqOut, dependencies=[Depends(AdminUser)])
async def patch_faq(item_id: UUID, body: FaqIn, session: AsyncSession = Depends(db_session)):
    item = await session.get(FaqItem, item_id)
    if item is None:
        raise NotFoundError("FAQ_NOT_FOUND", "FAQ entry not found")
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return FaqOut.model_validate(item)


@router.delete("/faq/{item_id}", status_code=204, dependencies=[Depends(AdminUser)])
async def delete_faq(item_id: UUID, session: AsyncSession = Depends(db_session)):
    item = await session.get(FaqItem, item_id)
    if item is None:
        raise NotFoundError("FAQ_NOT_FOUND", "FAQ entry not found")
    await session.delete(item)
    await session.commit()


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)):
    return DashboardOut.model_validate(await DashboardService(session).stats(actor))


@router.get("/cities", response_model=list[CityOut])
async def admin_cities(session: AsyncSession = Depends(db_session)):
    result = await session.execute(select(City).order_by(City.name))
    return [CityOut.model_validate(c) for c in result.scalars().all()]


@router.post("/cities", response_model=CityOut, status_code=201)
async def create_city(body: CityIn, session: AsyncSession = Depends(db_session)):
    city = City(**body.model_dump())
    session.add(city)
    await session.commit()
    await session.refresh(city)
    return CityOut.model_validate(city)


@router.patch("/cities/{city_id}", response_model=CityOut)
async def patch_city(city_id: UUID, body: CityIn, session: AsyncSession = Depends(db_session)):
    city = await session.get(City, city_id)
    if city is None:
        raise NotFoundError("CITY_NOT_FOUND", "City not found")
    for key, value in body.model_dump().items():
        setattr(city, key, value)
    await session.commit()
    await session.refresh(city)
    return CityOut.model_validate(city)


@router.post("/cities/{city_id}/deactivate", response_model=CityOut)
async def deactivate_city(city_id: UUID, session: AsyncSession = Depends(db_session)):
    city = await session.get(City, city_id)
    if city is None:
        raise NotFoundError("CITY_NOT_FOUND", "City not found")
    city.active = False
    await session.commit()
    await session.refresh(city)
    return CityOut.model_validate(city)


@router.get("/routes", response_model=list[RouteOut])
async def admin_routes(session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)):
    stmt = select(Route).options(selectinload(Route.origin_city), selectinload(Route.destination_city))
    if actor.role != UserRole.superadmin:
        stmt = stmt.where(Route.company_id == actor.company_id)
    result = await session.execute(stmt)
    return [RouteOut.model_validate(r) for r in result.scalars().all()]


@router.post("/routes", response_model=RouteOut, status_code=201)
async def create_route(
    body: RouteIn, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    company_id = _company_id(actor, body.company_id)
    route = Route(
        origin_city_id=body.origin_city_id,
        destination_city_id=body.destination_city_id,
        estimated_duration_minutes=body.estimated_duration_minutes,
        distance_km=body.distance_km,
        description=body.description,
        active=body.active,
        company_id=company_id,
    )
    session.add(route)
    await session.flush()
    session.add(
        RouteStop(
            route_id=route.id,
            city_id=body.origin_city_id,
            order_index=0,
            arrival_offset_minutes=0,
            departure_offset_minutes=0,
        )
    )
    session.add(
        RouteStop(
            route_id=route.id,
            city_id=body.destination_city_id,
            order_index=1,
            arrival_offset_minutes=body.estimated_duration_minutes,
            departure_offset_minutes=body.estimated_duration_minutes,
        )
    )
    await session.commit()
    result = await session.execute(
        select(Route)
        .options(selectinload(Route.origin_city), selectinload(Route.destination_city))
        .where(Route.id == route.id)
    )
    return RouteOut.model_validate(result.scalar_one())


@router.patch("/routes/{route_id}", response_model=RouteOut)
async def patch_route(
    route_id: UUID, body: RouteIn, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    route = await session.get(Route, route_id)
    if route is None:
        raise NotFoundError("ROUTE_NOT_FOUND", "Route not found")
    _company_id(actor, route.company_id)
    route.origin_city_id = body.origin_city_id
    route.destination_city_id = body.destination_city_id
    route.estimated_duration_minutes = body.estimated_duration_minutes
    route.distance_km = body.distance_km
    route.description = body.description
    route.active = body.active
    await session.commit()
    result = await session.execute(
        select(Route)
        .options(selectinload(Route.origin_city), selectinload(Route.destination_city))
        .where(Route.id == route.id)
    )
    return RouteOut.model_validate(result.scalar_one())


@router.post("/routes/{route_id}/deactivate", response_model=RouteOut)
async def deactivate_route(
    route_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    route = await session.get(Route, route_id)
    if route is None:
        raise NotFoundError("ROUTE_NOT_FOUND", "Route not found")
    _company_id(actor, route.company_id)
    route.active = False
    await session.commit()
    await session.refresh(route)
    return RouteOut.model_validate(route)


@router.get("/buses", response_model=list[BusOut])
async def admin_buses(session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)):
    stmt = select(Bus)
    if actor.role != UserRole.superadmin:
        stmt = stmt.where(Bus.company_id == actor.company_id)
    result = await session.execute(stmt.order_by(Bus.name))
    return [BusOut.model_validate(b) for b in result.scalars().all()]


@router.post("/buses", response_model=BusOut, status_code=201)
async def create_bus(body: BusIn, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)):
    bus = Bus(**{**body.model_dump(), "company_id": _company_id(actor, body.company_id)})
    session.add(bus)
    await session.commit()
    await session.refresh(bus)
    return BusOut.model_validate(bus)


@router.patch("/buses/{bus_id}", response_model=BusOut)
async def patch_bus(
    bus_id: UUID, body: BusIn, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    bus = await session.get(Bus, bus_id)
    if bus is None:
        raise NotFoundError("BUS_NOT_FOUND", "Bus not found")
    _company_id(actor, bus.company_id)
    bus.name = body.name
    bus.registration_number = body.registration_number
    bus.model = body.model
    bus.seat_count = body.seat_count
    bus.layout_type = body.layout_type
    bus.active = body.active
    await session.commit()
    await session.refresh(bus)
    return BusOut.model_validate(bus)


@router.get("/buses/{bus_id}/layout", response_model=BusLayoutOut)
async def get_layout(bus_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)):
    bus = await session.get(Bus, bus_id)
    if bus is None:
        raise NotFoundError("BUS_NOT_FOUND", "Bus not found")
    _company_id(actor, bus.company_id)
    result = await session.execute(
        select(BusLayout).options(selectinload(BusLayout.cells)).where(BusLayout.bus_id == bus_id)
    )
    layout = result.scalar_one_or_none()
    if layout is None:
        raise NotFoundError("LAYOUT_NOT_FOUND", "Layout not found")
    return BusLayoutOut(
        id=layout.id,
        bus_id=layout.bus_id,
        name=layout.name,
        rows=layout.rows,
        columns=layout.columns,
        active=layout.active,
        cells=[LayoutCellOut.model_validate(c) for c in layout.cells],
    )


@router.patch("/buses/{bus_id}/layout/cells", response_model=BusLayoutOut)
async def patch_layout_cells(
    bus_id: UUID,
    body: list[LayoutCellPatch],
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
):
    bus = await session.get(Bus, bus_id)
    if bus is None:
        raise NotFoundError("BUS_NOT_FOUND", "Bus not found")
    _company_id(actor, bus.company_id)
    result = await session.execute(
        select(BusLayout).options(selectinload(BusLayout.cells)).where(BusLayout.bus_id == bus_id)
    )
    layout = result.scalar_one_or_none()
    if layout is None:
        raise NotFoundError("LAYOUT_NOT_FOUND", "Layout not found")
    by_pos = {(c.row, c.column): c for c in layout.cells}
    for patch in body:
        cell = by_pos.get((patch.row, patch.column))
        if cell:
            cell.cell_type = patch.cell_type
    await session.commit()
    return await get_layout(bus_id, session, actor)


@router.post("/buses/{bus_id}/layout", response_model=BusLayoutOut, status_code=201)
async def generate_layout(
    bus_id: UUID,
    body: LayoutGenerateIn,
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
):
    """Create the seat plan for a bus. Rebuilds an existing plan only while no
    reservation has ever pointed at one of its seats."""
    bus = await session.get(Bus, bus_id)
    if bus is None:
        raise NotFoundError("BUS_NOT_FOUND", "Bus not found")
    _company_id(actor, bus.company_id)

    existing = (
        await session.execute(
            select(BusLayout).options(selectinload(BusLayout.cells)).where(BusLayout.bus_id == bus_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        used = (
            await session.execute(
                select(ReservationSeat.id).join(Seat, Seat.id == ReservationSeat.seat_id).where(Seat.bus_id == bus_id).limit(1)
            )
        ).first()
        if used:
            raise DomainError(
                "LAYOUT_IN_USE",
                "Seats of this bus already have reservations; the plan cannot be rebuilt",
                status_code=409,
            )
        for cell in existing.cells:
            await session.delete(cell)
        await session.flush()
        for seat in (await session.execute(select(Seat).where(Seat.bus_id == bus_id))).scalars().all():
            await session.delete(seat)
        await session.delete(existing)
        await session.flush()

    await build_coach_layout(
        session,
        bus,
        rows=body.rows,
        columns=body.columns,
        aisle_columns=set(body.aisle_columns),
        door_cells={(r, c) for r, c in body.door_cells},
        full_width_rows=set(body.full_width_rows),
        women_rows=set(body.women_rows),
        name=body.name,
    )
    await session.commit()
    return await get_layout(bus_id, session, actor)


@router.get("/trips", response_model=list[TripOut])
async def admin_trips(session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)):
    stmt = (
        select(Trip)
        .options(
            selectinload(Trip.route).selectinload(Route.origin_city),
            selectinload(Trip.route).selectinload(Route.destination_city),
            selectinload(Trip.bus),
        )
        .order_by(Trip.departure_datetime.desc())
    )
    if actor.role != UserRole.superadmin:
        stmt = stmt.where(Trip.company_id == actor.company_id)
    result = await session.execute(stmt)
    items = []
    service = TripService(session)
    for trip in result.scalars().all():
        payload = TripOut.model_validate(trip)
        payload.available_seats = await service.available_seats_count(trip)
        payload.route = RouteOut.model_validate(trip.route)
        payload.bus = BusOut.model_validate(trip.bus)
        items.append(payload)
    return items


@router.post("/trips", response_model=TripOut, status_code=201)
async def create_trip(
    body: TripCreateIn, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    company_id = _company_id(actor, body.company_id)
    trip = await TripService(session).create(
        route_id=body.route_id,
        bus_id=body.bus_id,
        company_id=company_id,
        departure_datetime=body.departure_datetime,
        base_price_minor=body.base_price_minor,
        currency=body.currency or get_settings().DEFAULT_CURRENCY,
        boarding_location=body.boarding_location,
        destination_location=body.destination_location,
        driver_id=None,
        actor_id=actor.id,
        status=body.status,
    )
    payload = TripOut.model_validate(trip)
    payload.route = RouteOut.model_validate(trip.route)
    payload.bus = BusOut.model_validate(trip.bus)
    return payload


@router.patch("/trips/{trip_id}", response_model=TripOut)
async def patch_trip(
    trip_id: UUID,
    body: TripPatchIn,
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
):
    trip = await session.get(Trip, trip_id, options=[selectinload(Trip.route)])
    if trip is None:
        raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
    _company_id(actor, trip.company_id)
    if body.departure_datetime is not None:
        trip.departure_datetime = body.departure_datetime
        trip.estimated_arrival_datetime = body.departure_datetime + timedelta(
            minutes=trip.route.estimated_duration_minutes
        )
    if body.base_price_minor is not None:
        trip.base_price_minor = body.base_price_minor
    if body.status is not None:
        trip.status = body.status
    if body.boarding_location is not None:
        trip.boarding_location = body.boarding_location
    if body.destination_location is not None:
        trip.destination_location = body.destination_location
    await session.commit()
    trip = await TripService(session).get(trip_id)
    payload = TripOut.model_validate(trip)
    payload.route = RouteOut.model_validate(trip.route)
    payload.bus = BusOut.model_validate(trip.bus)
    return payload


@router.post("/trips/{trip_id}/change-bus", response_model=TripOut)
async def change_bus(
    trip_id: UUID,
    body: TripBusChangeIn,
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
):
    trip = await session.get(Trip, trip_id)
    if trip is None:
        raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
    _company_id(actor, trip.company_id)
    trip = await TripService(session).change_bus(trip_id, body.bus_id, actor.id)
    return TripOut.model_validate(trip)


@router.post("/trips/{trip_id}/cancel", response_model=TripOut)
async def cancel_trip(
    trip_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    trip = await session.get(Trip, trip_id)
    if trip is None:
        raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
    _company_id(actor, trip.company_id)
    trip = await TripService(session).cancel_trip(trip_id, actor.id)
    return TripOut.model_validate(trip)


@router.get("/reservations", response_model=PageReservations)
async def list_reservations(
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    trip_id: UUID | None = None,
    status: ReservationStatus | None = None,
    phone: str | None = None,
    public_code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    data = await AdminListService(session).reservations(
        actor,
        page=page,
        page_size=page_size,
        trip_id=trip_id,
        status=status,
        phone=phone,
        public_code=public_code,
        date_from=date_from,
        date_to=date_to,
    )
    return PageReservations(
        items=[reservation_to_out(r) for r in data["items"]],
        page=data["page"],
        page_size=data["page_size"],
        total=data["total"],
    )


@router.post("/reservations/{reservation_id}/confirm", response_model=ReservationOut)
async def admin_confirm(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    reservation = await ReservationService(session).confirm(reservation_id, actor.id)
    return reservation_to_out(reservation)


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationOut)
async def admin_cancel(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    reservation = await ReservationService(session).cancel(reservation_id, actor.id)
    return reservation_to_out(reservation)


@router.post("/reservations/{reservation_id}/require-deposit", response_model=ReservationOut)
async def admin_require_deposit(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    reservation = await ReservationService(session).require_deposit(reservation_id, actor.id)
    return reservation_to_out(reservation)


@router.post("/reservations/{reservation_id}/reject", response_model=ReservationOut)
async def admin_reject(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    reservation = await ReservationService(session).reject(reservation_id, actor.id)
    return reservation_to_out(reservation)


@router.post("/reservations/{reservation_id}/mark-deposit-received", response_model=ReservationOut)
async def admin_deposit(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    reservation = await ReservationService(session).mark_deposit_received(reservation_id, actor.id)
    return reservation_to_out(reservation)


@router.post("/reservations/{reservation_id}/mark-no-show", response_model=ReservationOut)
async def admin_no_show(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    reservation = await ReservationService(session).mark_no_show(reservation_id, actor.id)
    return reservation_to_out(reservation)


@router.post("/reservations/{reservation_id}/mark-paid", response_model=PaymentOut)
async def admin_mark_paid(
    reservation_id: UUID, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    reservation = await ReservationService(session).get_by_id(reservation_id)
    _company_id(actor, reservation.company_id)
    payment = await PaymentService(session).mark_paid_offline(reservation_id, actor.id)
    return PaymentOut.model_validate(payment)


@router.get("/payments", response_model=PagePayments)
async def admin_payments(
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = await AdminListService(session).payments(actor, page, page_size)
    return PagePayments(
        items=[PaymentOut.model_validate(p) for p in data["items"]],
        page=data["page"],
        page_size=data["page_size"],
        total=data["total"],
    )


@router.get("/passengers", response_model=PagePassengers)
async def admin_passengers(
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = await AdminListService(session).passengers(actor, page, page_size)
    from app.schemas.booking import ReservationPassengerOut

    return PagePassengers(
        items=[ReservationPassengerOut.model_validate(p) for p in data["items"]],
        page=data["page"],
        page_size=data["page_size"],
        total=data["total"],
    )


@router.get("/users", response_model=PageUsers)
async def admin_users(
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = await AdminListService(session).users(actor, page, page_size)
    return PageUsers(
        items=[UserAdminOut.model_validate(u) for u in data["items"]],
        page=data["page"],
        page_size=data["page_size"],
        total=data["total"],
    )


@router.get("/companies", response_model=PageCompanies)
async def admin_companies(
    session: AsyncSession = Depends(db_session),
    actor: User = Depends(StaffUser),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = await AdminListService(session).companies(actor, page, page_size)
    return PageCompanies(
        items=[CompanyOut.model_validate(c) for c in data["items"]],
        page=data["page"],
        page_size=data["page_size"],
        total=data["total"],
    )


@router.post("/companies", response_model=CompanyOut, status_code=201)
async def create_company(
    body: CompanyIn, session: AsyncSession = Depends(db_session), actor: User = Depends(StaffUser)
):
    if actor.role != UserRole.superadmin:
        raise ForbiddenError("FORBIDDEN", "Only superadmin can create companies")
    company = TransportCompany(**body.model_dump())
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return CompanyOut.model_validate(company)
