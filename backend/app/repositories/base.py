from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


def apply_company_scope(stmt: Select, model, user_role: UserRole, company_id: UUID | None) -> Select:
    if user_role == UserRole.superadmin:
        return stmt
    if company_id is None:
        return stmt.where(func.false())
    return stmt.where(model.company_id == company_id)


def paginate_params(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    return page, page_size
