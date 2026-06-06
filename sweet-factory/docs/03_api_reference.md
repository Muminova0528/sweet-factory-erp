# Sweet Factory ERP — API Reference

Base URL: `http://localhost:8000/api/v1` (development) | `https://erp.sweetfactory.com/api/v1` (production)

All endpoints require `Authorization: Bearer <access_token>` unless noted.

---

## Authentication

### POST /auth/login
Login and receive JWT tokens.

**Request:**
```json
{ "username": "admin", "password": "Admin@123!" }
```
**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "uuid", "username": "admin", "role": "admin", "full_name": "..." }
}
```

### POST /auth/refresh
Exchange refresh token for new access token.

### GET /auth/me
Get current authenticated user profile.

### POST /auth/logout
Invalidate refresh token.

---

## ERP — Production

### GET /erp/products
List products. Query: `?page=1&limit=20&category=cakes&is_active=true`

### POST /erp/products *(admin, production_manager)*
Create product.
```json
{
  "name": "Victoria Sponge", "sku": "CAKE-001", "category": "cakes",
  "unit_price": 18.99, "cost_price": 6.50, "weight_grams": 500, "shelf_life_days": 14
}
```

### GET /erp/products/{id}
### PUT /erp/products/{id}
### DELETE /erp/products/{id}

### GET /erp/batches
List production batches. Query: `?status=in_progress`

### POST /erp/batches *(production_manager)*
Create batch.
```json
{ "product_id": "uuid", "quantity_planned": 100, "notes": "Christmas run" }
```

### PUT /erp/batches/{id}
Update batch (status, quantity_produced, notes).

### GET /erp/production/summary
Production summary statistics.

---

## CRM — Sales

### GET /crm/customers
### POST /crm/customers
```json
{
  "name": "Tesco PLC", "email": "orders@tesco.com",
  "phone": "+44-800-505-555", "company": "Tesco", "credit_limit": 50000
}
```
### GET /crm/customers/{id}
### GET /crm/customers/{id}/analytics
Order history, total spend, average order value.

### GET /crm/orders
### POST /crm/orders *(sales_manager)*
```json
{
  "customer_id": "uuid",
  "items": [{ "product_id": "uuid", "quantity": 10, "unit_price": 18.99 }],
  "notes": "Urgent delivery"
}
```
### PUT /crm/orders/{id}/status
```json
{ "status": "confirmed" }
```
Valid statuses: `pending → confirmed → processing → shipped → delivered | cancelled`

### GET /crm/sales/monthly
6-month revenue breakdown.

---

## WMS — Warehouse

### GET /wms/warehouses
### POST /wms/warehouses *(admin)*
### GET /wms/inventory
Query: `?warehouse_id=uuid&low_stock_only=true`
### GET /wms/inventory/stats
Count by status: in_stock, low_stock, out_of_stock.
### POST /wms/inventory/movements *(warehouse_manager)*
```json
{
  "inventory_id": "uuid",
  "movement_type": "in",
  "quantity": 50,
  "reference": "PO-2025-001"
}
```
Movement types: `in | out | adjustment | transfer`

### GET /wms/shipments
### POST /wms/shipments *(warehouse_manager)*
```json
{
  "order_id": "uuid", "warehouse_id": "uuid",
  "carrier": "DHL", "tracking_number": "1Z999AA"
}
```

---

## Dashboard

### GET /dashboard/stats
Returns all 8 KPI metrics in one call.

### GET /dashboard/sales-chart
6-month revenue data for chart rendering.

### GET /dashboard/inventory-by-category
Stock breakdown by product category.

---

## System

### GET /health *(no auth)*
```json
{ "status": "healthy", "database": "connected", "version": "2.0.0", "timestamp": "..." }
```

### GET /metrics *(no auth)*
```json
{ "cpu_percent": 12.4, "memory_percent": 34.2, "memory_mb": 342.1 }
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation error |
| 401 | Missing or invalid JWT |
| 403 | Insufficient role permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate SKU) |
| 422 | Unprocessable entity (schema error) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

Interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).
