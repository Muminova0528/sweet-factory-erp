#!/usr/bin/env python3
"""
Sweet Factory ERP - Database Seed Script
Populates the database with initial data for development and demo purposes.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, Customer, Supplier, Product, ProductCategory,
    RawMaterial, ProductIngredient, Warehouse, Inventory,
    ProductionBatch, BatchStatus
)


async def seed_database():
    """Main seed function."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("🌱 Starting database seed...")

        # ── Users ──────────────────────────────────────────────────────────────
        print("  Creating users...")
        users = [
            User(
                id=uuid.uuid4(),
                username="admin",
                email="admin@sweetfactory.com",
                hashed_password=get_password_hash("Admin@123!"),
                full_name="System Administrator",
                role=UserRole.admin,
                is_active=True,
            ),
            User(
                id=uuid.uuid4(),
                username="prod_manager",
                email="production@sweetfactory.com",
                hashed_password=get_password_hash("Prod@123!"),
                full_name="Ahmad Karimov",
                role=UserRole.production_manager,
                is_active=True,
            ),
            User(
                id=uuid.uuid4(),
                username="warehouse_mgr",
                email="warehouse@sweetfactory.com",
                hashed_password=get_password_hash("Ware@123!"),
                full_name="Nilufar Yusupova",
                role=UserRole.warehouse_manager,
                is_active=True,
            ),
            User(
                id=uuid.uuid4(),
                username="sales_mgr",
                email="sales@sweetfactory.com",
                hashed_password=get_password_hash("Sale@123!"),
                full_name="Bobur Rashidov",
                role=UserRole.sales_manager,
                is_active=True,
            ),
        ]
        session.add_all(users)
        await session.flush()

        # ── Suppliers ─────────────────────────────────────────────────────────
        print("  Creating suppliers...")
        suppliers = [
            Supplier(
                id=uuid.uuid4(),
                name="Premium Ingredients Ltd",
                email="orders@premiumingredients.com",
                phone="+44-20-1234-5678",
                address="12 Baker Street, London, UK",
                payment_terms=30,
            ),
            Supplier(
                id=uuid.uuid4(),
                name="Sweet Supplies Co",
                email="supply@sweetsupplies.com",
                phone="+44-20-9876-5432",
                address="45 Commerce Road, Manchester, UK",
                payment_terms=14,
            ),
        ]
        session.add_all(suppliers)
        await session.flush()

        # ── Raw Materials ─────────────────────────────────────────────────────
        print("  Creating raw materials...")
        raw_materials_data = [
            ("Wheat Flour", "kg", "0.45", "500", "100", 0),
            ("Sugar", "kg", "0.80", "300", "50", 0),
            ("Butter", "kg", "4.20", "150", "30", 0),
            ("Eggs", "dozen", "2.50", "80", "20", 0),
            ("Cocoa Powder", "kg", "6.50", "80", "15", 0),
            ("Dark Chocolate", "kg", "8.90", "60", "10", 1),
            ("Milk Chocolate", "kg", "7.50", "60", "10", 1),
            ("Vanilla Extract", "litre", "18.00", "20", "5", 0),
            ("Baking Powder", "kg", "2.10", "25", "5", 0),
            ("Salt", "kg", "0.30", "30", "5", 0),
            ("Cream", "litre", "2.80", "100", "20", 0),
            ("Packaging Boxes", "unit", "0.15", "2000", "500", 1),
        ]
        raw_materials = []
        for i, (name, unit, cost, stock, min_stock, supplier_idx) in enumerate(raw_materials_data):
            rm = RawMaterial(
                id=uuid.uuid4(),
                name=name,
                unit=unit,
                cost_per_unit=Decimal(cost),
                current_stock=Decimal(stock),
                minimum_stock=Decimal(min_stock),
                supplier_id=suppliers[supplier_idx].id,
            )
            raw_materials.append(rm)
        session.add_all(raw_materials)
        await session.flush()

        # ── Products ──────────────────────────────────────────────────────────
        print("  Creating products...")
        products_data = [
            ("Classic Victoria Sponge", "CAKE-001", ProductCategory.cakes, "Traditional British sponge cake", "18.99", "6.50"),
            ("Chocolate Fudge Cake", "CAKE-002", ProductCategory.cakes, "Rich dark chocolate layer cake", "22.50", "8.20"),
            ("Lemon Drizzle Cake", "CAKE-003", ProductCategory.cakes, "Zesty lemon sponge with drizzle", "16.99", "5.80"),
            ("Dark Chocolate Truffles (12pk)", "CHOC-001", ProductCategory.chocolates, "Premium dark chocolate truffles", "12.99", "4.20"),
            ("Milk Chocolate Bar (200g)", "CHOC-002", ProductCategory.chocolates, "Smooth milk chocolate bar", "3.49", "0.95"),
            ("Assorted Chocolate Box (24pk)", "CHOC-003", ProductCategory.chocolates, "Mixed selection of chocolates", "24.99", "8.50"),
            ("Classic Shortbread (250g)", "COOK-001", ProductCategory.cookies, "Traditional Scottish shortbread", "4.99", "1.20"),
            ("Chocolate Chip Cookies (300g)", "COOK-002", ProductCategory.cookies, "American-style cookies", "5.49", "1.60"),
            ("Ginger Snaps (200g)", "COOK-003", ProductCategory.cookies, "Crispy ginger biscuits", "3.99", "1.10"),
        ]
        products = []
        for name, sku, category, desc, price, cost in products_data:
            p = Product(
                id=uuid.uuid4(),
                name=name,
                sku=sku,
                category=category,
                description=desc,
                unit_price=Decimal(price),
                cost_price=Decimal(cost),
                weight_grams=500,
                shelf_life_days=14,
            )
            products.append(p)
        session.add_all(products)
        await session.flush()

        # ── Bill of Materials (sample) ─────────────────────────────────────────
        print("  Creating bill of materials...")
        # Victoria Sponge ingredients
        bom_data = [
            (products[0].id, raw_materials[0].id, "0.4"),   # Flour 400g
            (products[0].id, raw_materials[1].id, "0.3"),   # Sugar 300g
            (products[0].id, raw_materials[2].id, "0.25"),  # Butter 250g
            (products[0].id, raw_materials[3].id, "0.5"),   # Eggs (half dozen)
            # Chocolate cake
            (products[1].id, raw_materials[0].id, "0.35"),
            (products[1].id, raw_materials[1].id, "0.35"),
            (products[1].id, raw_materials[2].id, "0.30"),
            (products[1].id, raw_materials[4].id, "0.10"),  # Cocoa
            # Chocolate truffles
            (products[3].id, raw_materials[5].id, "0.15"),  # Dark choc
            (products[3].id, raw_materials[10].id, "0.05"), # Cream
            # Shortbread
            (products[6].id, raw_materials[0].id, "0.25"),
            (products[6].id, raw_materials[1].id, "0.12"),
            (products[6].id, raw_materials[2].id, "0.18"),
        ]
        ingredients = [
            ProductIngredient(
                id=uuid.uuid4(),
                product_id=p_id,
                raw_material_id=rm_id,
                quantity_per_unit=Decimal(qty),
            )
            for p_id, rm_id, qty in bom_data
        ]
        session.add_all(ingredients)
        await session.flush()

        # ── Warehouses ────────────────────────────────────────────────────────
        print("  Creating warehouses...")
        warehouses = [
            Warehouse(
                id=uuid.uuid4(),
                name="Main Production Warehouse",
                location="Unit 1, Industrial Estate, Birmingham, B1 1AA",
                capacity=10000,
            ),
            Warehouse(
                id=uuid.uuid4(),
                name="Cold Storage Facility",
                location="Unit 5, Refrigeration Park, Birmingham, B2 2BB",
                capacity=3000,
            ),
            Warehouse(
                id=uuid.uuid4(),
                name="Distribution Centre",
                location="Unit 12, Logistics Hub, Coventry, CV1 1AA",
                capacity=5000,
            ),
        ]
        session.add_all(warehouses)
        await session.flush()

        # ── Inventory ─────────────────────────────────────────────────────────
        print("  Creating inventory records...")
        inventory_records = []
        stock_levels = [
            # (product_idx, warehouse_idx, qty, reserved, reorder)
            (0, 0, 45, 5, 20),   # Victoria Sponge - Main WH
            (1, 0, 30, 8, 15),   # Choc Fudge - Main WH
            (2, 0, 52, 2, 20),   # Lemon Drizzle - Main WH
            (3, 1, 120, 20, 50), # Truffles - Cold Storage
            (4, 1, 300, 50, 100),# Choc Bar - Cold Storage
            (5, 1, 80, 10, 30),  # Assorted Box - Cold Storage
            (6, 2, 200, 30, 80), # Shortbread - DC
            (7, 2, 175, 25, 80), # Choc Chip - DC
            (8, 2, 220, 15, 80), # Ginger Snaps - DC
            (0, 2, 20, 0, 10),   # Victoria Sponge - DC
            (1, 2, 15, 0, 10),   # Choc Fudge - DC
        ]
        for p_idx, w_idx, qty, reserved, reorder in stock_levels:
            inv = Inventory(
                id=uuid.uuid4(),
                product_id=products[p_idx].id,
                warehouse_id=warehouses[w_idx].id,
                quantity_on_hand=qty,
                reserved_quantity=reserved,
                reorder_point=reorder,
            )
            inventory_records.append(inv)
        session.add_all(inventory_records)
        await session.flush()

        # ── Customers ─────────────────────────────────────────────────────────
        print("  Creating customers...")
        customers = [
            Customer(id=uuid.uuid4(), name="Tesco PLC", email="orders@tesco.com", phone="+44-800-505-555", company="Tesco PLC", credit_limit=Decimal("50000")),
            Customer(id=uuid.uuid4(), name="Waitrose Ltd", email="buying@waitrose.co.uk", phone="+44-800-188-884", company="John Lewis Partnership", credit_limit=Decimal("30000")),
            Customer(id=uuid.uuid4(), name="Marks & Spencer", email="food@marksandspencer.com", phone="+44-20-7935-4422", company="M&S Food", credit_limit=Decimal("40000")),
            Customer(id=uuid.uuid4(), name="The Coffee Shop Chain", email="supplies@coffeeshop.co.uk", phone="+44-121-456-7890", company="Coffee Shop Group Ltd", credit_limit=Decimal("15000")),
            Customer(id=uuid.uuid4(), name="Birmingham Bakeries Union", email="union@bhambakereis.co.uk", phone="+44-121-234-5678", company="BBU Co-op", credit_limit=Decimal("10000")),
        ]
        session.add_all(customers)
        await session.flush()

        # ── Production Batches ────────────────────────────────────────────────
        print("  Creating production batches...")
        now = datetime.utcnow()
        batches = [
            ProductionBatch(
                id=uuid.uuid4(),
                batch_number="BATCH-2025-001",
                product_id=products[0].id,
                quantity_planned=100,
                quantity_produced=100,
                status=BatchStatus.completed,
                started_at=now - timedelta(days=5),
                completed_at=now - timedelta(days=4),
                total_cost=Decimal("650.00"),
                created_by_id=users[1].id,
            ),
            ProductionBatch(
                id=uuid.uuid4(),
                batch_number="BATCH-2025-002",
                product_id=products[3].id,
                quantity_planned=200,
                quantity_produced=180,
                status=BatchStatus.completed,
                started_at=now - timedelta(days=3),
                completed_at=now - timedelta(days=2),
                total_cost=Decimal("840.00"),
                created_by_id=users[1].id,
            ),
            ProductionBatch(
                id=uuid.uuid4(),
                batch_number="BATCH-2025-003",
                product_id=products[1].id,
                quantity_planned=80,
                quantity_produced=40,
                status=BatchStatus.in_progress,
                started_at=now - timedelta(hours=6),
                created_by_id=users[1].id,
            ),
            ProductionBatch(
                id=uuid.uuid4(),
                batch_number="BATCH-2025-004",
                product_id=products[6].id,
                quantity_planned=150,
                status=BatchStatus.planned,
                created_by_id=users[1].id,
            ),
        ]
        session.add_all(batches)
        await session.commit()

        print("\n✅ Seed completed successfully!")
        print("\n📋 Login Credentials:")
        print("  Admin:      admin / Admin@123!")
        print("  Production: prod_manager / Prod@123!")
        print("  Warehouse:  warehouse_mgr / Ware@123!")
        print("  Sales:      sales_mgr / Sale@123!")
        print(f"\n  Products: {len(products)}")
        print(f"  Customers: {len(customers)}")
        print(f"  Warehouses: {len(warehouses)}")
        print(f"  Inventory records: {len(inventory_records)}")
        print(f"  Production batches: {len(batches)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
