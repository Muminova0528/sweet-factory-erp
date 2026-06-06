"""
Sweet Factory ERP — WMS Service
Warehouse, Inventory, and Shipment management business logic.
"""
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Warehouse, Inventory, StockMovement, Shipment,
    MovementType, ShipmentStatus, Product,
)
from app.schemas.schemas import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    InventoryResponse, StockMovementCreate,
)


class WMSService:
    """Warehouse and inventory management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Warehouses ───────────────────────────────────────────────────────────

    async def create_warehouse(self, data: WarehouseCreate) -> WarehouseResponse:
        existing = await self.session.execute(
            select(Warehouse).where(Warehouse.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Warehouse code '{data.code}' already exists",
            )

        warehouse = Warehouse(**data.model_dump())
        self.session.add(warehouse)
        await self.session.flush()
        await self.session.refresh(warehouse)
        return WarehouseResponse.model_validate(warehouse)

    async def get_warehouses(
        self,
        is_active: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Warehouse], int]:
        query = select(Warehouse).where(Warehouse.is_active == is_active)
        count_query = select(func.count()).select_from(Warehouse).where(
            Warehouse.is_active == is_active
        )
        query = query.offset(offset).limit(limit).order_by(Warehouse.name)
        warehouses = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return warehouses, total

    async def get_warehouse(self, warehouse_id: UUID) -> Warehouse:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found",
            )
        return warehouse

    # ─── Inventory ────────────────────────────────────────────────────────────

    async def get_inventory(
        self,
        warehouse_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        low_stock_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Inventory], int]:
        query = select(Inventory)
        count_query = select(func.count()).select_from(Inventory)

        if warehouse_id:
            query = query.where(Inventory.warehouse_id == warehouse_id)
            count_query = count_query.where(Inventory.warehouse_id == warehouse_id)

        if product_id:
            query = query.where(Inventory.product_id == product_id)
            count_query = count_query.where(Inventory.product_id == product_id)

        if low_stock_only:
            # Items where available quantity < 10 units
            low_stock_filter = (
                Inventory.quantity - Inventory.reserved_quantity
            ) < Decimal("10.000")
            query = query.where(low_stock_filter)
            count_query = count_query.where(low_stock_filter)

        query = query.offset(offset).limit(limit)
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return items, total

    async def record_stock_movement(
        self,
        data: StockMovementCreate,
        user_id: UUID,
    ) -> dict:
        """
        Record a stock movement (IN/OUT/ADJUSTMENT) and update inventory.
        """
        # Validate product & warehouse exist
        product = await self.session.get(Product, data.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        warehouse = await self.session.get(Warehouse, data.warehouse_id)
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        # Get or create inventory record
        inv_result = await self.session.execute(
            select(Inventory).where(
                and_(
                    Inventory.product_id == data.product_id,
                    Inventory.warehouse_id == data.warehouse_id,
                )
            )
        )
        inventory = inv_result.scalar_one_or_none()

        if not inventory:
            inventory = Inventory(
                product_id=data.product_id,
                warehouse_id=data.warehouse_id,
                quantity=Decimal("0.000"),
                reserved_quantity=Decimal("0.000"),
            )
            self.session.add(inventory)
            await self.session.flush()

        # Apply movement
        try:
            movement_type = MovementType(data.movement_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid movement type. Valid: {[m.value for m in MovementType]}",
            )

        if movement_type == MovementType.IN:
            inventory.quantity += data.quantity
        elif movement_type == MovementType.OUT:
            available = inventory.quantity - inventory.reserved_quantity
            if data.quantity > available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock. Available: {available}, Requested: {data.quantity}",
                )
            inventory.quantity -= data.quantity
        elif movement_type == MovementType.ADJUSTMENT:
            inventory.quantity = data.quantity  # Set absolute value

        # Record the movement
        movement = StockMovement(
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            movement_type=movement_type,
            quantity=data.quantity,
            reference_type=data.reference_type,
            unit_cost=data.unit_cost,
            notes=data.notes,
            created_by=user_id,
        )
        self.session.add(movement)
        await self.session.flush()

        return {
            "message": "Stock movement recorded",
            "movement_type": movement_type.value,
            "quantity": float(data.quantity),
            "new_stock_level": float(inventory.quantity),
        }

    async def get_inventory_stats(self) -> dict:
        """Total inventory statistics for dashboard."""
        result = await self.session.execute(
            select(
                func.count(Inventory.id).label("total_sku_locations"),
                func.sum(Inventory.quantity).label("total_units"),
                func.sum(Inventory.reserved_quantity).label("total_reserved"),
            )
        )
        row = result.one()

        # Count low stock items
        low_stock_result = await self.session.execute(
            select(func.count()).select_from(Inventory).where(
                (Inventory.quantity - Inventory.reserved_quantity) < Decimal("10.000")
            )
        )
        low_stock_count = low_stock_result.scalar_one()

        return {
            "total_sku_locations": row.total_sku_locations or 0,
            "total_units": float(row.total_units or 0),
            "total_reserved": float(row.total_reserved or 0),
            "low_stock_count": low_stock_count,
        }

    # ─── Shipments ────────────────────────────────────────────────────────────

    async def get_shipments(
        self,
        shipment_status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Shipment], int]:
        query = select(Shipment)
        count_query = select(func.count()).select_from(Shipment)

        if shipment_status:
            try:
                s = ShipmentStatus(shipment_status)
                query = query.where(Shipment.status == s)
                count_query = count_query.where(Shipment.status == s)
            except ValueError:
                pass

        query = query.offset(offset).limit(limit).order_by(Shipment.created_at.desc())
        shipments = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return shipments, total

    async def create_shipment(self, order_id: UUID, from_warehouse_id: UUID) -> dict:
        """Create a shipment for an order."""
        import uuid as uuid_module
        from datetime import datetime, timezone

        tracking = f"SF-{uuid_module.uuid4().hex[:12].upper()}"
        shipment = Shipment(
            tracking_number=tracking,
            order_id=order_id,
            from_warehouse_id=from_warehouse_id,
            status=ShipmentStatus.PENDING,
        )
        self.session.add(shipment)
        await self.session.flush()
        return {
            "tracking_number": tracking,
            "status": ShipmentStatus.PENDING.value,
            "message": "Shipment created successfully",
        }
