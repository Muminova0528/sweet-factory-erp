"""
Sweet Factory ERP — CRM API Endpoints
Customers, Distributors, and Orders.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth_middleware import get_current_user, require_sales
from app.models.models import User
from app.schemas.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    OrderCreate, OrderUpdate, OrderResponse,
    PaginatedResponse,
)
from app.services.crm_service import CRMService

router = APIRouter(prefix="/crm", tags=["CRM - Customer Relations"])


# ─── Customers ────────────────────────────────────────────────────────────────

@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_sales),
) -> CustomerResponse:
    return await CRMService(db).create_customer(data)


@router.get(
    "/customers",
    response_model=PaginatedResponse,
    summary="List customers",
)
async def list_customers(
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_distributor: Optional[bool] = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    customers, total = await CRMService(db).get_customers(
        search=search,
        is_distributor=is_distributor,
        is_active=is_active,
        offset=offset,
        limit=page_size,
    )
    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID",
)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CustomerResponse:
    customer = await CRMService(db).get_customer(customer_id)
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_sales),
) -> CustomerResponse:
    return await CRMService(db).update_customer(customer_id, data)


@router.get(
    "/customers/{customer_id}/analytics",
    summary="Customer analytics",
)
async def customer_analytics(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return await CRMService(db).get_customer_analytics(customer_id)


# ─── Orders ───────────────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_sales),
) -> OrderResponse:
    return await CRMService(db).create_order(data, created_by=current_user.id)


@router.get(
    "/orders",
    response_model=PaginatedResponse,
    summary="List orders",
)
async def list_orders(
    customer_id: Optional[UUID] = Query(None),
    order_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    orders, total = await CRMService(db).get_orders(
        customer_id=customer_id,
        order_status=order_status,
        offset=offset,
        limit=page_size,
    )
    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> OrderResponse:
    order = await CRMService(db).get_order(order_id)
    return OrderResponse.model_validate(order)


@router.patch(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Update order status",
)
async def update_order(
    order_id: UUID,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_sales),
) -> OrderResponse:
    return await CRMService(db).update_order_status(order_id, data)


@router.get(
    "/sales/monthly",
    summary="Monthly sales overview",
)
async def monthly_sales(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return await CRMService(db).get_monthly_sales()
