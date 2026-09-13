from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, ReservationSeat
from app.utils.time import utcnow


async def write_audit(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            created_at=utcnow(),
        )
    )


async def count_held_seats(session: AsyncSession, trip_id: UUID) -> int:
    result = await session.execute(
        select(func.count()).select_from(ReservationSeat).where(
            ReservationSeat.trip_id == trip_id,
            ReservationSeat.is_active_hold.is_(True),
        )
    )
    return int(result.scalar_one())
