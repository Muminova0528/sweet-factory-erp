"""
Sweet Factory ERP — Dashboard API
Aggregated KPIs and analytics for the main dashboard.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.models import (
    Customer, Order, OrderStatus,
    ProductionBatch, BatchStatus,
    Inventory, Shipment, ShipmentStatus,
    User,
)
from app.services.erp_service import ERPService
from app.services.crm_service import CRMService
from app.services.wms_service import WMSService

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get(
    "/stats",
    summary="Main dashboard statistics",
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """
    Returns aggregated KPIs:
    - Total active customers
    - Active orders count
    - Monthly production units
    - Low stock product count
    - Total revenue this month
    - Pending shipments
    - Production batches in progress
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total active customers
    customer_count = (await db.execute(
        select(func.count()).select_from(Customer).where(Customer.is_active == True)
    )).scalar_one()

    # Active orders (not cancelled, not delivered)
    active_orders = (await db.execute(
        select(func.count()).select_from(Order).where(
            Order.status.in_([
                OrderStatus.CONFIRMED,
                OrderStatus.IN_PRODUCTION,
                OrderStatus.READY,
                OrderStatus.SHIPPED,
            ])
        )
    )).scalar_one()

    # Monthly revenue
    monthly_revenue_result = (await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            and_(
                Order.order_date >= first_day_of_month,
                Order.status != OrderStatus.CANCELLED,
            )
        )
    )).scalar_one()

    # Monthly production (completed batches)
    production_summary = await ERPService(db).get_production_summary()

    # Inventory stats (low stock)
    inv_stats = await WMSService(db).get_inventory_stats()

    # Pending shipments
    pending_shipments = (await db.execute(
        select(func.count()).select_from(Shipment).where(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.DISPATCHED])
        )
    )).scalar_one()

    # Batches in progress
    in_progress_batches = (await db.execute(
        select(func.count()).select_from(ProductionBatch).where(
            ProductionBatch.status == BatchStatus.IN_PROGRESS
        )
    )).scalar_one()

    return {
        "total_customers": customer_count,
        "active_orders": active_orders,
        "monthly_production_units": production_summary["total_produced"],
        "low_stock_products": inv_stats["low_stock_count"],
        "total_revenue_this_month": float(monthly_revenue_result),
        "pending_shipments": pending_shipments,
        "production_batches_in_progress": in_progress_batches,
        "warehouse_total_units": inv_stats["total_units"],
    }


@router.get(
    "/sales-chart",
    summary="Sales data for charting (last 6 months)",
)
async def get_sales_chart(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    """Returns monthly sales totals for the last 6 months."""
    from datetime import datetime, timezone, timedelta
    import calendar

    now = datetime.now(timezone.utc)
    months = []

    for i in range(5, -1, -1):
        # Go back i months
        month_date = now.replace(day=1) - timedelta(days=i * 28)
        month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        _, last_day = calendar.monthrange(month_date.year, month_date.month)
        month_end = month_date.replace(day=last_day, hour=23, minute=59, second=59)

        result = (await db.execute(
            select(
                func.count(Order.id).label("orders"),
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            ).where(
                and_(
                    Order.order_date >= month_date,
                    Order.order_date <= month_end,
                    Order.status != OrderStatus.CANCELLED,
                )
            )
        )).one()

        months.append({
            "month": month_date.strftime("%b %Y"),
            "orders": result.orders,
            "revenue": float(result.revenue),
        })

    return months


@router.get(
    "/inventory-by-category",
    summary="Inventory breakdown by product category",
)
async def inventory_by_category(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    from app.models.models import Product
    from sqlalchemy.orm import aliased

    result = await db.execute(
        select(
            Product.category,
            func.sum(Inventory.quantity).label("total_quantity"),
            func.count(Inventory.id).label("sku_count"),
        )
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.category)
        .order_by(func.sum(Inventory.quantity).desc())
    )
    rows = result.all()
    return [
        {
            "category": row.category,
            "total_quantity": float(row.total_quantity),
            "sku_count": row.sku_count,
        }
        for row in rows
    ]
