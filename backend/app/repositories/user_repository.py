"""
Sweet Factory ERP — User Repository
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, offset: int = 0, limit: int = 20):
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
            .offset(offset)
            .limit(limit)
            .order_by(User.full_name)
        )
        return result.scalars().all()

    async def update_last_login(self, user_id: UUID) -> None:
        from datetime import datetime, timezone
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
