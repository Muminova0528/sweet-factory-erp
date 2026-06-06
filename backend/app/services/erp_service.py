"""
Sweet Factory ERP — ERP Service
Business logic for production management, batches, and ingredients.
"""
from decimal import Decimal
from typing import List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    Product, ProductionBatch, RawMaterial, ProductIngredient,
    BatchStatus, Inventory,
)
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    BatchCreate, BatchUpdate, BatchResponse,
)


class ERPService:
    """Handles production management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Products ────────────────────────────────────────────────────────────

    async def create_product(self, data: ProductCreate) -> ProductResponse:
        """Create a new product. SKU must be unique."""
        existing = await self.session.execute(
            select(Product).where(Product.sku == data.sku)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with SKU '{data.sku}' already exists",
            )

        product = Product(**data.model_dump())
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return ProductResponse.model_validate(product)

    async def get_products(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Product], int]:
        query = select(Product).where(Product.is_active == is_active)
        count_query = select(func.count()).select_from(Product).where(
            Product.is_active == is_active
        )

        if category:
            query = query.where(Product.category == category)
            count_query = count_query.where(Product.category == category)

        query = query.offset(offset).limit(limit).order_by(Product.name)
        products = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return products, total

    async def get_product(self, product_id: UUID) -> Product:
        result = await self.session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.ingredients))
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product

    async def update_product(self, product_id: UUID, data: ProductUpdate) -> ProductResponse:
        product = await self.get_product(product_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await self.session.flush()
        await self.session.refresh(product)
        return ProductResponse.model_validate(product)

    async def delete_product(self, product_id: UUID) -> None:
        """Soft delete — marks product as inactive."""
        product = await self.get_product(product_id)
        product.is_active = False
        await self.session.flush()

    # ─── Production Batches ───────────────────────────────────────────────────

    async def create_batch(self, data: BatchCreate, created_by: UUID) -> BatchResponse:
        """
        Create a production batch.
        Validates product exists and checks raw material availability.
        """
        # Validate product
        product_result = await self.session.execute(
            select(Product).where(and_(Product.id == data.product_id, Product.is_active == True))
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or inactive",
            )

        # Check batch number uniqueness
        existing = await self.session.execute(
            select(ProductionBatch).where(
                ProductionBatch.batch_number == data.batch_number
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch number '{data.batch_number}' already exists",
            )

        # Calculate estimated cost
        estimated_cost = await self._calculate_batch_cost(
            data.product_id, data.planned_quantity
        )

        batch = ProductionBatch(
            **data.model_dump(),
            status=BatchStatus.PLANNED,
            total_cost=estimated_cost,
            created_by=created_by,
        )
        self.session.add(batch)
        await self.session.flush()
        await self.session.refresh(batch)
        return BatchResponse.model_validate(batch)

    async def _calculate_batch_cost(
        self, product_id: UUID, quantity: Decimal
    ) -> Decimal:
        """Calculate total material cost for a production batch."""
        result = await self.session.execute(
            select(ProductIngredient, RawMaterial)
            .join(RawMaterial, ProductIngredient.raw_material_id == RawMaterial.id)
            .where(ProductIngredient.product_id == product_id)
        )
        rows = result.all()

        total_cost = Decimal("0.00")
        for ingredient, raw_material in rows:
            material_qty = ingredient.quantity_per_unit * quantity
            total_cost += material_qty * raw_material.unit_cost

        return total_cost

    async def get_batches(
        self,
        status: Optional[str] = None,
        product_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[ProductionBatch], int]:
        query = select(ProductionBatch)
        count_query = select(func.count()).select_from(ProductionBatch)

        if status:
            try:
                batch_status = BatchStatus(status)
                query = query.where(ProductionBatch.status == batch_status)
                count_query = count_query.where(ProductionBatch.status == batch_status)
            except ValueError:
                pass

        if product_id:
            query = query.where(ProductionBatch.product_id == product_id)
            count_query = count_query.where(ProductionBatch.product_id == product_id)

        query = query.offset(offset).limit(limit).order_by(
            ProductionBatch.planned_start.desc()
        )
        batches = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return batches, total

    async def update_batch(self, batch_id: UUID, data: BatchUpdate) -> BatchResponse:
        result = await self.session.execute(
            select(ProductionBatch).where(ProductionBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production batch not found",
            )

        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data:
            try:
                update_data["status"] = BatchStatus(update_data["status"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Valid values: {[s.value for s in BatchStatus]}",
                )

        for field, value in update_data.items():
            setattr(batch, field, value)

        await self.session.flush()
        await self.session.refresh(batch)
        return BatchResponse.model_validate(batch)

    async def get_production_summary(self) -> dict:
        """Monthly production summary for dashboard."""
        from datetime import datetime, timezone
        import calendar

        now = datetime.now(timezone.utc)
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.session.execute(
            select(
                func.count(ProductionBatch.id).label("total_batches"),
                func.sum(ProductionBatch.actual_quantity).label("total_produced"),
                func.sum(ProductionBatch.total_cost).label("total_cost"),
            ).where(
                and_(
                    ProductionBatch.created_at >= first_day,
                    ProductionBatch.status == BatchStatus.COMPLETED,
                )
            )
        )
        row = result.one()
        return {
            "total_batches": row.total_batches or 0,
            "total_produced": row.total_produced or Decimal("0"),
            "total_cost": row.total_cost or Decimal("0"),
        }
