from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
import app.models  # noqa: F401 — register all tables on Base.metadata
from app.models import (
    Bus,
    BusLayout,
    City,
    LayoutCell,
    LayoutCellType,
    Route,
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
from app.utils.time import utcnow

TEST_DATABASE_URL = get_settings().DATABASE_URL
if TEST_DATABASE_URL.rstrip("/").endswith("/nway"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.rstrip("/")[:-5] + "/nway_test"


async def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    db_name = parsed.database
    if not db_name:
        return
    admin_url = parsed.set(database="postgres")
    admin_engine = create_async_engine(admin_url.render_as_string(hide_password=False), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name})
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()


@pytest.fixture
async def engine():
    await _ensure_database(TEST_DATABASE_URL)
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest.fixture
async def world(session: AsyncSession) -> dict:
    company = TransportCompany(name="Test Co", phone="+998901000000", active=True)
    session.add(company)
    await session.flush()
    origin = City(name="Жезказган", country="KZ", timezone="Asia/Almaty", active=True)
    dest = City(name="Ташкент", country="UZ", timezone="Asia/Tashkent", active=True)
    session.add_all([origin, dest])
    await session.flush()
    route = Route(
        origin_city_id=origin.id,
        destination_city_id=dest.id,
        estimated_duration_minutes=840,
        distance_km=900,
        company_id=company.id,
        active=True,
    )
    session.add(route)
    await session.flush()
    bus = Bus(
        company_id=company.id,
        name="Test Bus",
        registration_number="TEST-1",
        model="Tourismo",
        seat_count=8,
        layout_type="2+2",
        active=True,
    )
    session.add(bus)
    await session.flush()
    layout = BusLayout(bus_id=bus.id, name="mini", rows=3, columns=5, active=True)
    session.add(layout)
    await session.flush()
    seats: list[Seat] = []
    for idx, (row, col, number) in enumerate(
        [(1, 0, "1A"), (1, 1, "1B"), (1, 3, "1C"), (1, 4, "1D"), (2, 0, "2A"), (2, 1, "2B"), (2, 3, "2C"), (2, 4, "2D")]
    ):
        seat = Seat(
            bus_id=bus.id,
            seat_number=number,
            row=row,
            column=col,
            type=SeatType.standard,
            active=True,
        )
        session.add(seat)
        await session.flush()
        seats.append(seat)
        session.add(
            LayoutCell(
                layout_id=layout.id,
                row=row,
                column=col,
                cell_type=LayoutCellType.seat,
                seat_id=seat.id,
            )
        )
    trip = Trip(
        route_id=route.id,
        bus_id=bus.id,
        company_id=company.id,
        departure_datetime=utcnow() + timedelta(days=2),
        estimated_arrival_datetime=utcnow() + timedelta(days=2, hours=14),
        status=TripStatus.scheduled,
        base_price_minor=1_000_000,
        currency="UZS",
        boarding_location="A",
        destination_location="B",
    )
    session.add(trip)
    admin = User(
        phone="+998909999999",
        email="admin@example.com",
        password_hash=hash_password("secret"),
        role=UserRole.admin,
        status=UserStatus.active,
        phone_verified=True,
        company_id=company.id,
        first_name="Admin",
    )
    session.add(admin)
    await session.flush()
    session.add(UserStats(user_id=admin.id))
    await session.commit()
    return {
        "company": company,
        "origin": origin,
        "dest": dest,
        "route": route,
        "bus": bus,
        "seats": seats,
        "trip": trip,
        "admin": admin,
        "session": session,
    }


@pytest.fixture
async def client(engine, session: AsyncSession, world) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
