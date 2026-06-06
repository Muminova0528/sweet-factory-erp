"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="employee"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("company", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("outstanding_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )
    op.create_index("ix_customers_email", "customers", ["email"])

    # --- suppliers ---
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("payment_terms", sa.Integer(), nullable=False, server_default="30"),
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
    )

    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
    )
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_category", "products", ["category"])

    # --- raw_materials ---
    op.create_table(
        "raw_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("cost_per_unit", sa.Numeric(10, 4), nullable=False),
        sa.Column("current_stock", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("minimum_stock", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_raw_materials_supplier"),
        sa.PrimaryKeyConstraint("id", name="pk_raw_materials"),
    )

    # --- product_ingredients (Bill of Materials) ---
    op.create_table(
        "product_ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_per_unit", sa.Numeric(10, 4), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_pi_product", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_materials.id"], name="fk_pi_raw_material"),
        sa.PrimaryKeyConstraint("id", name="pk_product_ingredients"),
        sa.UniqueConstraint("product_id", "raw_material_id", name="uq_product_ingredient"),
    )

    # --- production_batches ---
    op.create_table(
        "production_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("batch_number", sa.String(50), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_planned", sa.Integer(), nullable=False),
        sa.Column("quantity_produced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_batch_product"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_batch_user"),
        sa.PrimaryKeyConstraint("id", name="pk_production_batches"),
        sa.UniqueConstraint("batch_number", name="uq_batch_number"),
    )
    op.create_index("ix_production_batches_status", "production_batches", ["status"])

    # --- warehouses ---
    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
    )

    # --- inventory ---
    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="10"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_inventory_product"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_inventory_warehouse"),
        sa.PrimaryKeyConstraint("id", name="pk_inventory"),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )

    # --- stock_movements ---
    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventory.id"], name="fk_movement_inventory"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_movement_user"),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
    )

    # --- orders ---
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("order_number", sa.String(50), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("expected_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_order_customer"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_order_user"),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.UniqueConstraint("order_number", name="uq_order_number"),
    )
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_customer", "orders", ["customer_id"])

    # --- order_items ---
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_orderitem_order", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_orderitem_product"),
        sa.PrimaryKeyConstraint("id", name="pk_order_items"),
    )

    # --- shipments ---
    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="preparing"),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("carrier", sa.String(100), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_shipment_order"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_shipment_warehouse"),
        sa.PrimaryKeyConstraint("id", name="pk_shipments"),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_audit_user"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_table_record", "audit_logs", ["table_name", "record_id"])
    op.create_index("ix_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("shipments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("stock_movements")
    op.drop_table("inventory")
    op.drop_table("warehouses")
    op.drop_table("production_batches")
    op.drop_table("product_ingredients")
    op.drop_table("raw_materials")
    op.drop_table("products")
    op.drop_table("suppliers")
    op.drop_table("customers")
    op.drop_table("users")
