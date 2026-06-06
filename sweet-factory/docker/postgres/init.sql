-- =============================================================================
-- Sweet Factory ERP - PostgreSQL Initialization Script
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create application database (if not exists via env)
-- Note: DB is created by POSTGRES_DB env var; this script runs inside it

-- Create application role with limited privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sweetfactory_app') THEN
        CREATE ROLE sweetfactory_app WITH LOGIN PASSWORD 'app_password_change_in_prod';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE sweetfactory TO sweetfactory_app;
GRANT USAGE ON SCHEMA public TO sweetfactory_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sweetfactory_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO sweetfactory_app;

-- =============================================================================
-- Performance Configuration Comments
-- =============================================================================
-- The following settings are recommended in postgresql.conf for production:
--   max_connections = 200
--   shared_buffers = 256MB
--   effective_cache_size = 768MB
--   maintenance_work_mem = 64MB
--   checkpoint_completion_target = 0.9
--   wal_buffers = 16MB
--   default_statistics_target = 100
--   random_page_cost = 1.1
--   effective_io_concurrency = 200
--   work_mem = 4MB
--   min_wal_size = 1GB
--   max_wal_size = 4GB

-- =============================================================================
-- Audit Log Function (auto-populate audit trail)
-- =============================================================================
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (id, table_name, record_id, action, old_values, new_values, created_at)
        VALUES (
            uuid_generate_v4(),
            TG_TABLE_NAME,
            OLD.id,
            'DELETE',
            row_to_json(OLD),
            NULL,
            NOW()
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_logs (id, table_name, record_id, action, old_values, new_values, created_at)
        VALUES (
            uuid_generate_v4(),
            TG_TABLE_NAME,
            NEW.id,
            'UPDATE',
            row_to_json(OLD),
            row_to_json(NEW),
            NOW()
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (id, table_name, record_id, action, old_values, new_values, created_at)
        VALUES (
            uuid_generate_v4(),
            TG_TABLE_NAME,
            NEW.id,
            'INSERT',
            NULL,
            row_to_json(NEW),
            NOW()
        );
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Inventory Alert Function
-- =============================================================================
CREATE OR REPLACE FUNCTION check_low_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.quantity_on_hand < NEW.reorder_point THEN
        RAISE NOTICE 'LOW STOCK ALERT: Product % in warehouse % has % units (reorder point: %)',
            NEW.product_id, NEW.warehouse_id, NEW.quantity_on_hand, NEW.reorder_point;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helpful Views (created after tables exist via Alembic)
-- =============================================================================

-- This function creates views after tables are set up
CREATE OR REPLACE FUNCTION create_application_views()
RETURNS void AS $$
BEGIN
    -- Dashboard summary view
    EXECUTE '
        CREATE OR REPLACE VIEW v_dashboard_summary AS
        SELECT
            (SELECT COUNT(*) FROM orders WHERE status NOT IN (''delivered'', ''cancelled'')) AS active_orders,
            (SELECT COUNT(*) FROM production_batches WHERE status IN (''planned'', ''in_progress'')) AS active_batches,
            (SELECT COUNT(*) FROM inventory WHERE quantity_on_hand < reorder_point) AS low_stock_items,
            (SELECT COALESCE(SUM(total_amount), 0) FROM orders
             WHERE created_at >= date_trunc(''month'', NOW())) AS monthly_revenue,
            (SELECT COUNT(*) FROM customers WHERE is_active = true) AS active_customers,
            (SELECT COUNT(*) FROM users WHERE is_active = true) AS active_users;
    ';

    -- Monthly sales view
    EXECUTE '
        CREATE OR REPLACE VIEW v_monthly_sales AS
        SELECT
            DATE_TRUNC(''month'', created_at) AS month,
            COUNT(*) AS order_count,
            SUM(total_amount) AS total_revenue,
            AVG(total_amount) AS avg_order_value
        FROM orders
        WHERE status != ''cancelled''
        GROUP BY DATE_TRUNC(''month'', created_at)
        ORDER BY month DESC;
    ';

    -- Inventory status view
    EXECUTE '
        CREATE OR REPLACE VIEW v_inventory_status AS
        SELECT
            p.name AS product_name,
            p.sku,
            p.category,
            w.name AS warehouse_name,
            i.quantity_on_hand,
            i.reserved_quantity,
            i.quantity_on_hand - i.reserved_quantity AS available_quantity,
            i.reorder_point,
            CASE
                WHEN i.quantity_on_hand = 0 THEN ''out_of_stock''
                WHEN i.quantity_on_hand < i.reorder_point THEN ''low_stock''
                ELSE ''in_stock''
            END AS stock_status
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN warehouses w ON i.warehouse_id = w.id;
    ';
END;
$$ LANGUAGE plpgsql;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION audit_trigger_func() TO sweetfactory_app;
GRANT EXECUTE ON FUNCTION check_low_stock() TO sweetfactory_app;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Sweet Factory ERP database initialized successfully at %', NOW();
END
$$;
