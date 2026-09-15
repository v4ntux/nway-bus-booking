import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    Bus,
    BusLayout,
    City,
    LayoutCell,
    LayoutCellType,
    Route,
    RouteStop,
    Seat,
    SeatType,
    TransportCompany,
    Trip,
    TripStatus,
    User,
    UserRole,
    UserStats,
    UserStatus,
)
from app.utils.phone import normalize_phone
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# Uzbekistan has no daylight saving: a fixed offset avoids needing tzdata on the host.
TASHKENT = timezone(timedelta(hours=5), "Asia/Tashkent")

# name, lat, lng
CITIES = [
    ("Toshkent", 41.2995, 69.2401),
    ("Samarqand", 39.6542, 66.9597),
    ("Buxoro", 39.7681, 64.4556),
    ("Farg‘ona", 40.3864, 71.7864),
    ("Andijon", 40.7821, 72.3442),
    ("Namangan", 40.9983, 71.6726),
    ("Nukus", 42.4531, 59.6103),
    ("Urganch", 41.5500, 60.6333),
    ("Termiz", 37.2242, 67.2783),
    ("Qarshi", 38.8606, 65.7891),
    ("Navoiy", 40.0844, 65.3792),
    ("Jizzax", 40.1158, 67.8422),
]

# origin, destination, minutes, km, departures (local Tashkent time), price in so'm
ROUTES = [
    ("Toshkent", "Samarqand", 4 * 60 + 30, 310, ((7, 0), (12, 0), (18, 30)), 95_000),
    ("Samarqand", "Toshkent", 4 * 60 + 30, 310, ((6, 30), (13, 0), (19, 0)), 95_000),
    ("Toshkent", "Buxoro", 8 * 60 + 30, 580, ((8, 0), (21, 0)), 160_000),
    ("Buxoro", "Toshkent", 8 * 60 + 30, 580, ((8, 0), (21, 30)), 160_000),
    ("Toshkent", "Farg‘ona", 5 * 60, 320, ((7, 30), (15, 0)), 110_000),
    ("Farg‘ona", "Toshkent", 5 * 60, 320, ((7, 0), (16, 0)), 110_000),
    ("Toshkent", "Andijon", 6 * 60, 360, ((8, 30), (20, 0)), 120_000),
    ("Andijon", "Toshkent", 6 * 60, 360, ((7, 0), (19, 30)), 120_000),
    ("Toshkent", "Termiz", 10 * 60, 700, ((9, 0), (20, 30)), 190_000),
    ("Termiz", "Toshkent", 10 * 60, 700, ((8, 0), (20, 0)), 190_000),
    ("Toshkent", "Urganch", 16 * 60, 1000, ((17, 0),), 260_000),
    ("Urganch", "Toshkent", 16 * 60, 1000, ((17, 0),), 260_000),
    ("Toshkent", "Nukus", 18 * 60, 1150, ((16, 0),), 290_000),
    ("Nukus", "Toshkent", 18 * 60, 1150, ((16, 0),), 290_000),
    ("Samarqand", "Buxoro", 4 * 60, 270, ((9, 0), (17, 0)), 80_000),
    ("Buxoro", "Samarqand", 4 * 60, 270, ((9, 0), (17, 0)), 80_000),
    ("Toshkent", "Qarshi", 7 * 60, 520, ((8, 0), (22, 0)), 150_000),
    ("Qarshi", "Toshkent", 7 * 60, 520, ((8, 0), (22, 0)), 150_000),
]

BUSES = [
    ("Yutong 01", "01 A 123 BC", "Yutong ZK6122H9"),
    ("Tourismo 02", "01 B 456 CD", "Mercedes-Benz Tourismo"),
    ("Yutong 03", "30 C 789 DE", "Yutong ZK6127H"),
]


SCHEDULE_DAYS = 10


async def refresh_trip_schedule(
    session: AsyncSession, *, company: TransportCompany | None = None
) -> int:
    """Top up the demo schedule so the next SCHEDULE_DAYS days always have trips.

    Idempotent: a departure already on a route is never duplicated, so this is safe
    to run on every boot. Returns the number of trips added.
    """
    settings = get_settings()
    if company is None:
        company = (
            await session.execute(select(TransportCompany).where(TransportCompany.name == "NWay Trans"))
        ).scalar_one_or_none()
        if company is None:
            return 0

    buses = list(
        (
            await session.scalars(
                select(Bus).where(Bus.company_id == company.id, Bus.active.is_(True)).order_by(Bus.registration_number)
            )
        ).all()
    )
    if not buses:
        return 0

    cities = {city.name: city for city in (await session.scalars(select(City))).all()}
    routes = {
        (route.origin_city_id, route.destination_city_id): route
        for route in (await session.scalars(select(Route).where(Route.company_id == company.id))).all()
    }

    now = utcnow()
    today_local = now.astimezone(TASHKENT).date()
    bus_cursor = 0
    added = 0
    for origin_name, dest_name, minutes, _km, departures, price_som in ROUTES:
        origin, destination = cities.get(origin_name), cities.get(dest_name)
        if not origin or not destination:
            continue
        route = routes.get((origin.id, destination.id))
        if route is None:
            continue
        taken = set(
            (await session.scalars(select(Trip.departure_datetime).where(Trip.route_id == route.id))).all()
        )
        for day_offset in range(SCHEDULE_DAYS):
            day = today_local + timedelta(days=day_offset)
            for hour, minute in departures:
                local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TASHKENT)
                departure = local.astimezone(timezone.utc)
                if departure <= now or departure in taken:
                    continue
                bus = buses[bus_cursor % len(buses)]
                bus_cursor += 1
                session.add(
                    Trip(
                        route_id=route.id,
                        bus_id=bus.id,
                        company_id=company.id,
                        departure_datetime=departure,
                        estimated_arrival_datetime=departure + timedelta(minutes=minutes),
                        status=TripStatus.scheduled,
                        base_price_minor=price_som * 100,
                        currency=settings.DEFAULT_CURRENCY,
                        boarding_location=f"{origin_name} avtovokzali",
                        destination_location=f"{dest_name} avtovokzali",
                    )
                )
                taken.add(departure)
                added += 1

    await session.commit()
    return added


async def seed_database(session: AsyncSession) -> None:
    settings = get_settings()
    existing = (
        await session.execute(select(TransportCompany).where(TransportCompany.name == "NWay Trans"))
    ).scalar_one_or_none()
    if existing:
        # Everything else is already in place, but the schedule is a rolling
        # window — without this the demo runs out of trips ten days after seeding.
        added = await refresh_trip_schedule(session, company=existing)
        logger.info("seed_skip reason=already_present trips_added=%s", added)
        return

    company = TransportCompany(name="NWay Trans", phone="+998712000000", active=True)
    session.add(company)
    await session.flush()

    cities: dict[str, City] = {}
    for name, lat, lng in CITIES:
        city = City(name=name, country="UZ", timezone="Asia/Tashkent", lat=lat, lng=lng, active=True)
        session.add(city)
        cities[name] = city
    await session.flush()

    buses: list[Bus] = []
    for name, plate, model in BUSES:
        bus = Bus(
            company_id=company.id,
            name=name,
            registration_number=plate,
            model=model,
            seat_count=0,
            layout_type="2+2",
            active=True,
        )
        session.add(bus)
        await session.flush()
        await build_coach_layout(session, bus)
        buses.append(bus)

    superadmin = User(
        phone=normalize_phone(settings.SEED_ADMIN_PHONE),
        first_name="Super",
        last_name="Admin",
        email=settings.SEED_SUPERADMIN_EMAIL.lower(),
        password_hash=hash_password(settings.SEED_SUPERADMIN_PASSWORD),
        role=UserRole.superadmin,
        status=UserStatus.active,
        phone_verified=True,
        company_id=None,
    )
    admin_email = settings.SEED_ADMIN_EMAIL.lower()
    if admin_email == settings.SEED_SUPERADMIN_EMAIL.lower():
        # Emails are unique; the superadmin keeps the configured address.
        admin_email = "admin@demo.local"
    admin = User(
        phone="+998712000001",
        first_name="Dilnoza",
        last_name="Karimova",
        email=admin_email,
        password_hash=hash_password(settings.SEED_ADMIN_PASSWORD),
        role=UserRole.admin,
        status=UserStatus.active,
        phone_verified=True,
        company_id=company.id,
    )
    passenger = User(
        phone=normalize_phone(settings.SEED_PASSENGER_PHONE),
        first_name="Ali",
        last_name="Demo",
        role=UserRole.passenger,
        status=UserStatus.active,
        phone_verified=True,
    )
    session.add_all([superadmin, admin, passenger])
    await session.flush()
    session.add_all(
        [
            UserStats(user_id=superadmin.id),
            UserStats(user_id=admin.id),
            UserStats(user_id=passenger.id),
        ]
    )

    now = utcnow()
    today_local = now.astimezone(TASHKENT).date()
    bus_cursor = 0
    trips_added = 0
    for origin_name, dest_name, minutes, km, departures, price_som in ROUTES:
        origin = cities[origin_name]
        destination = cities[dest_name]
        route = Route(
            origin_city_id=origin.id,
            destination_city_id=destination.id,
            estimated_duration_minutes=minutes,
            distance_km=km,
            description=f"{origin_name} - {dest_name}",
            active=True,
            company_id=company.id,
        )
        session.add(route)
        await session.flush()
        session.add_all(
            [
                RouteStop(
                    route_id=route.id,
                    city_id=origin.id,
                    order_index=0,
                    arrival_offset_minutes=0,
                    departure_offset_minutes=0,
                ),
                RouteStop(
                    route_id=route.id,
                    city_id=destination.id,
                    order_index=1,
                    arrival_offset_minutes=minutes,
                    departure_offset_minutes=minutes,
                ),
            ]
        )

        for day_offset in range(0, 10):
            day = today_local + timedelta(days=day_offset)
            for hour, minute in departures:
                local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TASHKENT)
                departure = local.astimezone(timezone.utc)
                if departure <= now:
                    continue
                bus = buses[bus_cursor % len(buses)]
                bus_cursor += 1
                session.add(
                    Trip(
                        route_id=route.id,
                        bus_id=bus.id,
                        company_id=company.id,
                        departure_datetime=departure,
                        estimated_arrival_datetime=departure + timedelta(minutes=minutes),
                        status=TripStatus.scheduled,
                        base_price_minor=price_som * 100,
                        currency=settings.DEFAULT_CURRENCY,
                        boarding_location=f"{origin_name} avtovokzali",
                        destination_location=f"{dest_name} avtovokzali",
                    )
                )
                trips_added += 1

    await session.commit()
    logger.info("seed_complete company=%s trips=%s", company.name, trips_added)


# Coach geometry, seen from above with the driver at row 0.
# 2 + aisle + 2, thirteen rows: the passenger-facing grid is 13 x 5.
COACH_ROWS = 13
COACH_COLUMNS = 5
AISLE_COLUMNS = {2}
# Kerb-side (right) doors: one behind the driver, one before the rear bench.
DOOR_CELLS = {(1, 3), (1, 4), (11, 3), (11, 4)}
# The rear bench spans the whole width, no aisle.
FULL_WIDTH_ROWS = {12}
# Front rows are held for women travelling alone.
WOMEN_ROWS = {0, 1, 2, 3}


async def build_coach_layout(
    session: AsyncSession,
    bus: Bus,
    *,
    rows: int = COACH_ROWS,
    columns: int = COACH_COLUMNS,
    aisle_columns: set[int] | None = None,
    door_cells: set[tuple[int, int]] | None = None,
    full_width_rows: set[int] | None = None,
    women_rows: set[int] | None = None,
    name: str = "2+2 coach",
) -> int:
    """Create seats and layout cells for a bus. Seats are numbered 1..N
    front to back, left to right. Returns the seat count."""
    aisle_columns = AISLE_COLUMNS if aisle_columns is None else aisle_columns
    door_cells = DOOR_CELLS if door_cells is None else door_cells
    full_width_rows = FULL_WIDTH_ROWS if full_width_rows is None else full_width_rows
    women_rows = WOMEN_ROWS if women_rows is None else women_rows

    layout = BusLayout(bus_id=bus.id, name=name, rows=rows, columns=columns, active=True)
    session.add(layout)
    await session.flush()

    seat_count = 0
    for row in range(rows):
        for col in range(columns):
            if (row, col) in door_cells:
                cell_type = LayoutCellType.door
            elif row in full_width_rows:
                cell_type = LayoutCellType.seat
            elif col in aisle_columns:
                cell_type = LayoutCellType.aisle
            else:
                cell_type = LayoutCellType.seat

            seat = None
            if cell_type == LayoutCellType.seat:
                seat_count += 1
                seat = Seat(
                    bus_id=bus.id,
                    seat_number=str(seat_count),
                    row=row,
                    column=col,
                    type=SeatType.standard,
                    active=True,
                    is_accessibility=(row == 0 and col < min(aisle_columns, default=columns)),
                    is_premium=(row in {0, 1, 2}),
                    is_women_only=(row in women_rows),
                )
                session.add(seat)
                await session.flush()

            session.add(
                LayoutCell(
                    layout_id=layout.id,
                    row=row,
                    column=col,
                    cell_type=cell_type,
                    seat_id=seat.id if seat else None,
                    x=col,
                    y=row,
                )
            )
    bus.seat_count = seat_count
    logger.info("layout_seeded bus=%s seats=%s", bus.name, seat_count)
    return seat_count
