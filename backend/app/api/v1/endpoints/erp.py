"""
Sweet Factory ERP — ERP API Endpoints
Products and Production Batch management.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth_middleware import get_current_user, require_production
from app.models.models import User
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    BatchCreate, BatchUpdate, BatchResponse,
    PaginatedResponse,
)
from app.services.erp_service import ERPService

router = APIRouter(prefix="/erp", tags=["ERP - Production Management"])


# ─── Products ────────────────────────────────────────────────────────────────

@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_production),
) -> ProductResponse:
    return await ERPService(db).create_product(data)


@router.get(
    "/products",
    response_model=PaginatedResponse,
    summary="List all products",
)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    products, total = await ERPService(db).get_products(
        category=category, is_active=is_active, offset=offset, limit=page_size
    )
    return PaginatedResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProductResponse:
    product = await ERPService(db).get_product(product_id)
    return ProductResponse.model_validate(product)


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_production),
) -> ProductResponse:
    return await ERPService(db).update_product(product_id, data)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate product (soft delete)",
)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_production),
) -> None:
    await ERPService(db).delete_product(product_id)


# ─── Production Batches ───────────────────────────────────────────────────────

@router.post(
    "/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a production batch",
)
async def create_batch(
    data: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_production),
) -> BatchResponse:
    return await ERPService(db).create_batch(data, created_by=current_user.id)


@router.get(
    "/batches",
    response_model=PaginatedResponse,
    summary="List production batches",
)
async def list_batches(
    batch_status: Optional[str] = Query(None, alias="status"),
    product_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse:
    offset = (page - 1) * page_size
    batches, total = await ERPService(db).get_batches(
        status=batch_status, product_id=product_id, offset=offset, limit=page_size
    )
    return PaginatedResponse(
        items=[BatchResponse.model_validate(b) for b in batches],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.patch(
    "/batches/{batch_id}",
    response_model=BatchResponse,
    summary="Update production batch status",
)
async def update_batch(
    batch_id: UUID,
    data: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_production),
) -> BatchResponse:
    return await ERPService(db).update_batch(batch_id, data)


@router.get(
    "/production/summary",
    summary="Monthly production summary",
)
async def production_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return await ERPService(db).get_production_summary()
