from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DomainError, NotFoundError
from app.models import Ticket, TicketStatus, Trip
from app.models.route import Route


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_public_id(self, public_id: str) -> Ticket:
        result = await self.session.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.passenger),
                selectinload(Ticket.seat),
                selectinload(Ticket.trip).selectinload(Trip.route).selectinload(Route.origin_city),
                selectinload(Ticket.trip).selectinload(Trip.route).selectinload(Route.destination_city),
                selectinload(Ticket.reservation),
            )
            .where(Ticket.public_id == public_id.strip().upper())
        )
        ticket = result.scalar_one_or_none()
        if ticket is None:
            raise NotFoundError("TICKET_NOT_FOUND", "Ticket not found")
        return ticket

    async def verify_qr(self, qr_token: str) -> Ticket:
        result = await self.session.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.passenger),
                selectinload(Ticket.seat),
                selectinload(Ticket.trip),
            )
            .where(Ticket.qr_token == qr_token.strip())
        )
        ticket = result.scalar_one_or_none()
        if ticket is None:
            raise NotFoundError("TICKET_NOT_FOUND", "Ticket not found")
        if ticket.status == TicketStatus.cancelled:
            raise DomainError("TICKET_CANCELLED", "Ticket is cancelled", status_code=409)
        if ticket.status == TicketStatus.used:
            raise DomainError("TICKET_ALREADY_USED", "Ticket already used", status_code=409)
        ticket.status = TicketStatus.used
        await self.session.commit()
        return ticket

    async def list_for_reservation(self, reservation_id) -> list[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.passenger), selectinload(Ticket.seat))
            .where(Ticket.reservation_id == reservation_id)
        )
        return list(result.scalars().all())
