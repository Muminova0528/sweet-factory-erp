"""
Sweet Factory ERP — CRM Service
Customer, Distributor, and Order management business logic.
"""
import uuid
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Customer, Order, OrderItem, OrderStatus, Product
from app.schemas.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    OrderCreate, OrderUpdate, OrderResponse,
)


class CRMService:
    """Customer and order management business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Customers ────────────────────────────────────────────────────────────

    async def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        """Create a new customer or distributor."""
        existing = await self.session.execute(
            select(Customer).where(Customer.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this email already exists",
            )

        customer = Customer(**data.model_dump())
        self.session.add(customer)
        await self.session.flush()
        await self.session.refresh(customer)
        return CustomerResponse.model_validate(customer)

    async def get_customers(
        self,
        search: Optional[str] = None,
        is_distributor: Optional[bool] = None,
        is_active: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Customer], int]:
        query = select(Customer).where(Customer.is_active == is_active)
        count_query = select(func.count()).select_from(Customer).where(
            Customer.is_active == is_active
        )

        if search:
            search_filter = or_(
                Customer.company_name.ilike(f"%{search}%"),
                Customer.contact_name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if is_distributor is not None:
            query = query.where(Customer.is_distributor == is_distributor)
            count_query = count_query.where(Customer.is_distributor == is_distributor)

        query = query.offset(offset).limit(limit).order_by(Customer.company_name)
        customers = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return customers, total

    async def get_customer(self, customer_id: UUID) -> Customer:
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return customer

    async def update_customer(self, customer_id: UUID, data: CustomerUpdate) -> CustomerResponse:
        customer = await self.get_customer(customer_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        await self.session.flush()
        await self.session.refresh(customer)
        return CustomerResponse.model_validate(customer)

    async def get_customer_analytics(self, customer_id: UUID) -> dict:
        """Order analytics for a specific customer."""
        await self.get_customer(customer_id)  # Ensure exists

        result = await self.session.execute(
            select(
                func.count(Order.id).label("total_orders"),
                func.sum(Order.total_amount).label("lifetime_value"),
                func.max(Order.order_date).label("last_order_date"),
            ).where(
                and_(
                    Order.customer_id == customer_id,
                    Order.status != OrderStatus.CANCELLED,
                )
            )
        )
        row = result.one()
        return {
            "customer_id": str(customer_id),
            "total_orders": row.total_orders or 0,
            "lifetime_value": row.lifetime_value or Decimal("0"),
            "last_order_date": row.last_order_date,
        }

    # ─── Orders ───────────────────────────────────────────────────────────────

    async def create_order(self, data: OrderCreate, created_by: UUID) -> OrderResponse:
        """
        Create a new order with line items.
        Auto-calculates totals and generates order number.
        """
        # Validate customer
        customer = await self.get_customer(data.customer_id)

        # Generate unique order number
        order_number = await self._generate_order_number()

        # Calculate totals
        subtotal = Decimal("0.00")
        order_items = []

        for item_data in data.items:
            # Validate product
            product_result = await self.session.execute(
                select(Product).where(
                    and_(Product.id == item_data.product_id, Product.is_active == True)
                )
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item_data.product_id} not found",
                )

            item_discount = item_data.discount_percent / Decimal("100")
            item_total = item_data.quantity * item_data.unit_price * (1 - item_discount)
            subtotal += item_total

            order_items.append(
                OrderItem(
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    discount_percent=item_data.discount_percent,
                    total_price=item_total,
                )
            )

        order_discount = data.discount_percent / Decimal("100")
        discounted_subtotal = subtotal * (1 - order_discount)
        tax_amount = discounted_subtotal * Decimal("0.12")
        total_amount = discounted_subtotal + tax_amount

        order = Order(
            order_number=order_number,
            customer_id=data.customer_id,
            status=OrderStatus.DRAFT,
            delivery_date=data.delivery_date,
            shipping_address=data.shipping_address or customer.address,
            discount_percent=data.discount_percent,
            tax_percent=Decimal("12.00"),
            subtotal=subtotal,
            total_amount=total_amount,
            notes=data.notes,
            created_by=created_by,
            order_items=order_items,
        )

        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)

        # Reload with relationships
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.order_items))
        )
        order_with_items = result.scalar_one()
        return OrderResponse.model_validate(order_with_items)

    async def get_orders(
        self,
        customer_id: Optional[UUID] = None,
        order_status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Order], int]:
        query = select(Order).options(selectinload(Order.order_items))
        count_query = select(func.count()).select_from(Order)

        if customer_id:
            query = query.where(Order.customer_id == customer_id)
            count_query = count_query.where(Order.customer_id == customer_id)

        if order_status:
            try:
                s = OrderStatus(order_status)
                query = query.where(Order.status == s)
                count_query = count_query.where(Order.status == s)
            except ValueError:
                pass

        query = query.offset(offset).limit(limit).order_by(Order.order_date.desc())
        orders = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_query)).scalar_one()
        return orders, total

    async def get_order(self, order_id: UUID) -> Order:
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.order_items))
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return order

    async def update_order_status(self, order_id: UUID, data: OrderUpdate) -> OrderResponse:
        order = await self.get_order(order_id)

        if data.status:
            try:
                order.status = OrderStatus(data.status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Valid: {[s.value for s in OrderStatus]}",
                )

        if data.delivery_date:
            order.delivery_date = data.delivery_date
        if data.notes:
            order.notes = data.notes

        await self.session.flush()
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)

    async def get_monthly_sales(self) -> dict:
        """Sales summary for the current month."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.session.execute(
            select(
                func.count(Order.id).label("total_orders"),
                func.sum(Order.total_amount).label("total_revenue"),
            ).where(
                and_(
                    Order.order_date >= first_day,
                    Order.status != OrderStatus.CANCELLED,
                )
            )
        )
        row = result.one()
        return {
            "month": now.strftime("%B %Y"),
            "total_orders": row.total_orders or 0,
            "total_revenue": row.total_revenue or Decimal("0"),
        }

    async def _generate_order_number(self) -> str:
        """Generate sequential order number: ORD-2024-000001"""
        from datetime import datetime, timezone
        year = datetime.now(timezone.utc).year

        result = await self.session.execute(
            select(func.count(Order.id)).where(
                Order.order_number.like(f"ORD-{year}-%")
            )
        )
        count = result.scalar_one() + 1
        return f"ORD-{year}-{count:06d}"
