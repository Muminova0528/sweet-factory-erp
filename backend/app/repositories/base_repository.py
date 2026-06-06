"""
Sweet Factory ERP — Base Repository
Generic async CRUD repository using Repository Pattern.
"""
from typing import TypeVar, Generic, Type, Optional, List, Sequence
from uuid import UUID

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository implementing CRUD operations.
    All child repositories inherit from this class.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """Fetch a single record by its UUID primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[ModelType]:
        """Fetch paginated list of records."""
        result = await self.session.execute(
            select(self.model)
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().all()

    async def count(self) -> int:
        """Count total records."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def create(self, entity: ModelType) -> ModelType:
        """Persist a new entity to the database."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing entity."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete a record by ID.
        Returns True if deleted, False if not found.
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == entity_id)
        )
        return result.rowcount > 0

    async def exists(self, entity_id: UUID) -> bool:
        """Check if a record exists by ID."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(
                self.model.id == entity_id
            )
        )
        return result.scalar_one() > 0
