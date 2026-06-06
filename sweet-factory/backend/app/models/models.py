"""
Sweet Factory ERP — Database Models
Complete ORM model definitions for all business entities.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, Text,
    ForeignKey, Enum as SAEnum, func, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─── Enumerations ────────────────────────────────────────────────────────────
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PRODUCTION_MANAGER = "production_manager"
    WAREHOUSE_MANAGER = "warehouse_manager"
    SALES_MANAGER = "sales_manager"
    EMPLOYEE = "employee"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PRODUCTION = "in_production"
    READY = "ready"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class BatchStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RETURNED = "returned"


class MovementType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


# ─── Mixins ──────────────────────────────────────────────────────────────────
class TimestampMixin:
    """Adds created_at and updated_at timestamps to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """UUID primary key mixin."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


# ─── Users & Auth ────────────────────────────────────────────────────────────
class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"


# ─── CRM Models ──────────────────────────────────────────────────────────────
class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    tax_id: Mapped[Optional[str]] = mapped_column(String(100))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_distributor: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    orders: Mapped[List["Order"]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.company_name}>"


class Supplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suppliers"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)

    # Relationships
    raw_materials: Mapped[List["RawMaterial"]] = relationship(back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier {self.company_name}>"


# ─── ERP Models ──────────────────────────────────────────────────────────────
class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # cake, chocolate, cookie
    unit: Mapped[str] = mapped_column(String(50), default="kg")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    weight_grams: Mapped[Optional[int]] = mapped_column(Integer)
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    production_batches: Mapped[List["ProductionBatch"]] = relationship(back_populates="product")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="product")
    inventory: Mapped[List["Inventory"]] = relationship(back_populates="product")
    ingredients: Mapped[List["ProductIngredient"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<Product {self.sku}: {self.name}>"


class RawMaterial(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "raw_materials"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="kg")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0.000"))
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0.000"))
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("suppliers.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    supplier: Mapped[Optional["Supplier"]] = relationship(back_populates="raw_materials")
    product_ingredients: Mapped[List["ProductIngredient"]] = relationship(
        back_populates="raw_material"
    )

    def __repr__(self) -> str:
        return f"<RawMaterial {self.code}: {self.name}>"


class ProductIngredient(Base, TimestampMixin):
    """Bill of Materials — links products to their raw material ingredients."""
    __tablename__ = "product_ingredients"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), primary_key=True
    )
    raw_material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_materials.id"), primary_key=True
    )
    quantity_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="kg")

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="ingredients")
    raw_material: Mapped["RawMaterial"] = relationship(back_populates="product_ingredients")


class ProductionBatch(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "production_batches"

    batch_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    actual_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    status: Mapped[BatchStatus] = mapped_column(
        SAEnum(BatchStatus), default=BatchStatus.PLANNED, nullable=False
    )
    planned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    planned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="production_batches")

    def __repr__(self) -> str:
        return f"<ProductionBatch {self.batch_number} [{self.status}]>"


# ─── WMS Models ──────────────────────────────────────────────────────────────
class Warehouse(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100), default="Uzbekistan")
    capacity_sqm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    temperature_controlled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    inventory: Mapped[List["Inventory"]] = relationship(back_populates="warehouse")
    shipments_from: Mapped[List["Shipment"]] = relationship(
        back_populates="from_warehouse",
        foreign_keys="Shipment.from_warehouse_id",
    )

    def __repr__(self) -> str:
        return f"<Warehouse {self.code}: {self.name}>"


class Inventory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inventory"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0.000"))
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0.000"))
    lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="inventory")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "lot_number", name="uq_inventory_product_warehouse_lot"),
        Index("ix_inventory_product_warehouse", "product_id", "warehouse_id"),
    )

    @property
    def available_quantity(self) -> Decimal:
        return self.quantity - self.reserved_quantity

    def __repr__(self) -> str:
        return f"<Inventory product={self.product_id} qty={self.quantity}>"


class StockMovement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "stock_movements"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(SAEnum(MovementType), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(100))  # order, batch, etc.
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


# ─── Order Models ────────────────────────────────────────────────────────────
class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.DRAFT, nullable=False
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("12.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    shipping_address: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    shipments: Mapped[List["Shipment"]] = relationship(back_populates="order")

    def __repr__(self) -> str:
        return f"<Order {self.order_number} [{self.status}]>"


class OrderItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="order_items")
    product: Mapped["Product"] = relationship(back_populates="order_items")


class Shipment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shipments"

    tracking_number: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("orders.id"))
    from_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus), default=ShipmentStatus.PENDING
    )
    carrier: Mapped[Optional[str]] = mapped_column(String(255))
    shipping_address: Mapped[Optional[str]] = mapped_column(Text)
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    order: Mapped[Optional["Order"]] = relationship(back_populates="shipments")
    from_warehouse: Mapped[Optional["Warehouse"]] = relationship(
        back_populates="shipments_from", foreign_keys=[from_warehouse_id]
    )


# ─── Audit Log ───────────────────────────────────────────────────────────────
class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
    )
