"""
Sweet Factory ERP — WMS API Endpoints
Warehouses, Inventory tracking, and Shipments.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth_middleware import get_current_user, require_warehouse
from app.models.models import User
from app.schemas.schemas import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    InventoryResponse, StockMovementCreate,
    PaginatedResponse,
)
from app.services.wms_service import WMSService

router = APIRouter(prefix="/wms", tags=["WMS - Warehouse Management"])


# ─── Warehouses ───────────────────────────────────────────────────────────────

@router.post(
    "/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new warehouse",
)
async def create_warehouse(
    data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_warehouse),
) -> WarehouseResponse:
    return await WMSService(db).create_warehouse(data)


@router.get(
    "/warehouses",
    response_model=PaginatedResponse,
    summary="List warehouses",
)
async def list_warehouses(
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    warehouses, total = await WMSService(db).get_warehouses(
        is_active=is_active, offset=offset, limit=page_size
    )
    return PaginatedResponse(
        items=[WarehouseResponse.model_validate(w) for w in warehouses],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Get warehouse by ID",
)
async def get_warehouse(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WarehouseResponse:
    warehouse = await WMSService(db).get_warehouse(warehouse_id)
    return WarehouseResponse.model_validate(warehouse)


# ─── Inventory ────────────────────────────────────────────────────────────────

@router.get(
    "/inventory",
    response_model=PaginatedResponse,
    summary="List inventory",
)
async def list_inventory(
    warehouse_id: Optional[UUID] = Query(None),
    product_id: Optional[UUID] = Query(None),
    low_stock_only: bool = Query(False, description="Show only low-stock items"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    items, total = await WMSService(db).get_inventory(
        warehouse_id=warehouse_id,
        product_id=product_id,
        low_stock_only=low_stock_only,
        offset=offset,
        limit=page_size,
    )

    # Build response with available_quantity computed property
    response_items = []
    for inv in items:
        response_items.append({
            "id": str(inv.id),
            "product_id": str(inv.product_id),
            "warehouse_id": str(inv.warehouse_id),
            "quantity": float(inv.quantity),
            "reserved_quantity": float(inv.reserved_quantity),
            "available_quantity": float(inv.available_quantity),
            "lot_number": inv.lot_number,
            "expiry_date": inv.expiry_date.isoformat() if inv.expiry_date else None,
        })

    return PaginatedResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/inventory/movements",
    status_code=status.HTTP_201_CREATED,
    summary="Record stock movement (IN/OUT/ADJUSTMENT)",
)
async def record_stock_movement(
    data: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_warehouse),
) -> dict:
    """
    Record a stock movement:
    - **IN**: Add stock (receiving shipment, production output)
    - **OUT**: Remove stock (order fulfillment)
    - **ADJUSTMENT**: Set absolute quantity (stocktake result)
    """
    return await WMSService(db).record_stock_movement(data, user_id=current_user.id)


@router.get(
    "/inventory/stats",
    summary="Inventory statistics for dashboard",
)
async def inventory_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return await WMSService(db).get_inventory_stats()


# ─── Shipments ────────────────────────────────────────────────────────────────

@router.get(
    "/shipments",
    response_model=PaginatedResponse,
    summary="List shipments",
)
async def list_shipments(
    shipment_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    shipments, total = await WMSService(db).get_shipments(
        shipment_status=shipment_status, offset=offset, limit=page_size
    )
    response_items = []
    for s in shipments:
        response_items.append({
            "id": str(s.id),
            "tracking_number": s.tracking_number,
            "order_id": str(s.order_id) if s.order_id else None,
            "status": s.status.value,
            "carrier": s.carrier,
            "dispatched_at": s.dispatched_at.isoformat() if s.dispatched_at else None,
            "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
        })
    return PaginatedResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/shipments",
    status_code=status.HTTP_201_CREATED,
    summary="Create shipment for an order",
)
async def create_shipment(
    order_id: UUID,
    from_warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_warehouse),
) -> dict:
    return await WMSService(db).create_shipment(order_id, from_warehouse_id)
