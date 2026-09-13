from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import City, Route, RouteStop, TransportCompany, User, UserStats
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self.session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


class CompanyRepository(BaseRepository):
    async def get(self, company_id: UUID) -> TransportCompany | None:
        return await self.session.get(TransportCompany, company_id)


class CityRepository(BaseRepository):
    async def list_active(self) -> list[City]:
        result = await self.session.execute(
            select(City).where(City.active.is_(True)).order_by(City.name)
        )
        return list(result.scalars().all())

    async def get(self, city_id: UUID) -> City | None:
        return await self.session.get(City, city_id)


class RouteRepository(BaseRepository):
    async def get(self, route_id: UUID) -> Route | None:
        result = await self.session.execute(
            select(Route)
            .options(selectinload(Route.origin_city), selectinload(Route.destination_city), selectinload(Route.stops).selectinload(RouteStop.city))
            .where(Route.id == route_id)
        )
        return result.scalar_one_or_none()
