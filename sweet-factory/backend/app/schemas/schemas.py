"""
Sweet Factory ERP — Pydantic Schemas
Request/Response data validation and serialization.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


# ─── Base Schemas ────────────────────────────────────────────────────────────
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Auth Schemas ────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str = "employee"

    @model_validator(mode="after")
    def validate_password_strength(self):
        password = self.password
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
        return self


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseSchema):
    id: UUID
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# ─── Customer Schemas ────────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    contact_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: Decimal = Field(default=Decimal("0.00"), ge=0)
    is_distributor: bool = False
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CustomerResponse(BaseSchema):
    id: UUID
    company_name: str
    contact_name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    credit_limit: Decimal
    is_distributor: bool
    is_active: bool
    created_at: datetime


# ─── Product Schemas ─────────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    sku: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    category: str = Field(min_length=2, max_length=100)
    unit: str = "kg"
    unit_price: Decimal = Field(gt=0)
    cost_price: Decimal = Field(gt=0)
    weight_grams: Optional[int] = Field(default=None, gt=0)
    shelf_life_days: Optional[int] = Field(default=None, gt=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseSchema):
    id: UUID
    sku: str
    name: str
    description: Optional[str]
    category: str
    unit: str
    unit_price: Decimal
    cost_price: Decimal
    weight_grams: Optional[int]
    shelf_life_days: Optional[int]
    is_active: bool
    created_at: datetime


# ─── Production Batch Schemas ────────────────────────────────────────────────
class BatchCreate(BaseModel):
    batch_number: str = Field(min_length=3, max_length=100)
    product_id: UUID
    planned_quantity: Decimal = Field(gt=0)
    planned_start: datetime
    planned_end: datetime
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.planned_end <= self.planned_start:
            raise ValueError("planned_end must be after planned_start")
        return self


class BatchUpdate(BaseModel):
    status: Optional[str] = None
    actual_quantity: Optional[Decimal] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    notes: Optional[str] = None


class BatchResponse(BaseSchema):
    id: UUID
    batch_number: str
    product_id: UUID
    planned_quantity: Decimal
    actual_quantity: Optional[Decimal]
    status: str
    planned_start: datetime
    planned_end: datetime
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    total_cost: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime


# ─── Order Schemas ───────────────────────────────────────────────────────────
class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class OrderCreate(BaseModel):
    customer_id: UUID
    delivery_date: Optional[datetime] = None
    shipping_address: Optional[str] = None
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    notes: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    delivery_date: Optional[datetime] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class OrderItemResponse(BaseSchema):
    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal
    total_price: Decimal


class OrderResponse(BaseSchema):
    id: UUID
    order_number: str
    customer_id: UUID
    status: str
    order_date: datetime
    delivery_date: Optional[datetime]
    subtotal: Decimal
    discount_percent: Decimal
    tax_percent: Decimal
    total_amount: Decimal
    shipping_address: Optional[str]
    notes: Optional[str]
    order_items: List[OrderItemResponse] = []
    created_at: datetime


# ─── Warehouse & Inventory Schemas ───────────────────────────────────────────
class WarehouseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = None
    capacity_sqm: Optional[Decimal] = None
    temperature_controlled: bool = False


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    is_active: Optional[bool] = None


class WarehouseResponse(BaseSchema):
    id: UUID
    name: str
    code: str
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    capacity_sqm: Optional[Decimal]
    is_active: bool
    temperature_controlled: bool
    created_at: datetime


class InventoryResponse(BaseSchema):
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    lot_number: Optional[str]
    expiry_date: Optional[datetime]


class StockMovementCreate(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    movement_type: str
    quantity: Decimal = Field(gt=0)
    reference_type: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    notes: Optional[str] = None


# ─── Dashboard Schemas ───────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_customers: int
    active_orders: int
    monthly_production_units: Decimal
    low_stock_products: int
    total_revenue_this_month: Decimal
    pending_shipments: int
    production_batches_in_progress: int
    warehouse_utilization_percent: float


class SalesOverview(BaseModel):
    month: str
    total_orders: int
    total_revenue: Decimal
    new_customers: int
