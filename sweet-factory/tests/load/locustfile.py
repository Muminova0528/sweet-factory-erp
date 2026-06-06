"""
Sweet Factory ERP — Load Testing with Locust
BTEC Unit 6: C.M3 — Performance & Scalability Testing

Tests:
- 100 users  → baseline performance
- 500 users  → moderate load
- 1000 users → high load
- 2000 users → stress test

Run:
    # 100 users
    locust -f tests/load/locustfile.py --host=https://sweetfactory.com \
           --users 100 --spawn-rate 10 --run-time 5m --headless

    # Stress test: 2000 users
    locust -f tests/load/locustfile.py --host=https://sweetfactory.com \
           --users 2000 --spawn-rate 50 --run-time 10m --headless

    # Web UI (open http://localhost:8089)
    locust -f tests/load/locustfile.py --host=http://localhost:80
"""
import json
import random
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# ─── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "/api/v1"

# Test user credentials (seeded in database)
TEST_USERS = [
    {"email": "admin@sweetfactory.com", "password": "Admin@2024!"},
    {"email": "sales@sweetfactory.com", "password": "Sales@2024!"},
    {"email": "warehouse@sweetfactory.com", "password": "Warehouse@2024!"},
    {"email": "production@sweetfactory.com", "password": "Production@2024!"},
]


# ─── Metrics Collection ───────────────────────────────────────────────────────
response_times = []
error_count = 0
request_count = 0


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    global request_count
    request_count += 1
    response_times.append(response_time)


@events.request.add_listener
def on_request_failure(request_type, name, response_time, exception, **kwargs):
    global error_count
    error_count += 1


# ─── Base User ────────────────────────────────────────────────────────────────
class BaseERPUser(HttpUser):
    """Base class with authentication setup."""

    abstract = True
    access_token = None

    def on_start(self):
        """Login before running tasks."""
        credentials = random.choice(TEST_USERS)
        self.login(credentials["email"], credentials["password"])

    def login(self, email: str, password: str) -> bool:
        with self.client.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            catch_response=True,
            name="POST /auth/login",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.client.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                })
                return True
            else:
                response.failure(f"Login failed: {response.status_code}")
                return False


# ─── Read-heavy User (70% of traffic) ─────────────────────────────────────────
class ReadUser(BaseERPUser):
    """
    Simulates typical dashboard/reporting user.
    Predominantly read operations — mirrors real-world traffic patterns.
    """
    weight = 7  # 70% of users
    wait_time = between(1, 5)  # 1-5 seconds between tasks

    @task(5)
    def view_dashboard(self):
        """Most common action — view dashboard."""
        self.client.get(
            f"{BASE_URL}/dashboard/stats",
            name="GET /dashboard/stats",
        )

    @task(4)
    def view_orders(self):
        self.client.get(
            f"{BASE_URL}/crm/orders?page=1&page_size=20",
            name="GET /crm/orders",
        )

    @task(4)
    def view_inventory(self):
        self.client.get(
            f"{BASE_URL}/wms/inventory?page=1&page_size=50",
            name="GET /wms/inventory",
        )

    @task(3)
    def view_customers(self):
        self.client.get(
            f"{BASE_URL}/crm/customers?page=1&page_size=20",
            name="GET /crm/customers",
        )

    @task(3)
    def view_products(self):
        self.client.get(
            f"{BASE_URL}/erp/products?page=1&page_size=20",
            name="GET /erp/products",
        )

    @task(2)
    def view_batches(self):
        self.client.get(
            f"{BASE_URL}/erp/batches?page=1&page_size=20",
            name="GET /erp/batches",
        )

    @task(2)
    def view_sales_chart(self):
        self.client.get(
            f"{BASE_URL}/dashboard/sales-chart",
            name="GET /dashboard/sales-chart",
        )

    @task(2)
    def view_warehouses(self):
        self.client.get(
            f"{BASE_URL}/wms/warehouses",
            name="GET /wms/warehouses",
        )

    @task(1)
    def view_shipments(self):
        self.client.get(
            f"{BASE_URL}/wms/shipments?page=1&page_size=20",
            name="GET /wms/shipments",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="GET /health")


# ─── Write User (30% of traffic) ──────────────────────────────────────────────
class WriteUser(BaseERPUser):
    """
    Simulates operational staff performing data entry.
    Mix of reads and writes — more realistic business operations.
    """
    weight = 3  # 30% of users
    wait_time = between(3, 10)  # Slower — humans filling forms

    def on_start(self):
        super().on_start()
        # Use admin credentials for write operations
        self.login("admin@sweetfactory.com", "Admin@2024!")

    @task(3)
    def create_order(self):
        """Create a new customer order."""
        # First get a customer ID
        customers_resp = self.client.get(
            f"{BASE_URL}/crm/customers?page=1&page_size=5",
            name="GET /crm/customers (for order)",
        )
        if customers_resp.status_code != 200:
            return

        customers_data = customers_resp.json()
        if not customers_data.get("items"):
            return

        customer_id = customers_data["items"][0]["id"]

        # Get a product
        products_resp = self.client.get(
            f"{BASE_URL}/erp/products?page=1&page_size=5",
            name="GET /erp/products (for order)",
        )
        if products_resp.status_code != 200:
            return

        products_data = products_resp.json()
        if not products_data.get("items"):
            return

        product = products_data["items"][0]

        # Create order
        self.client.post(
            f"{BASE_URL}/crm/orders",
            json={
                "customer_id": customer_id,
                "delivery_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "discount_percent": "0.00",
                "notes": f"Load test order {random.randint(1000, 9999)}",
                "items": [
                    {
                        "product_id": product["id"],
                        "quantity": str(random.randint(1, 50)),
                        "unit_price": str(product["unit_price"]),
                        "discount_percent": "0.00",
                    }
                ],
            },
            name="POST /crm/orders",
        )

    @task(2)
    def record_stock_movement(self):
        """Record stock IN movement."""
        # Get inventory context
        inv_resp = self.client.get(
            f"{BASE_URL}/wms/inventory?page=1&page_size=3",
            name="GET /wms/inventory (for movement)",
        )
        if inv_resp.status_code != 200 or not inv_resp.json().get("items"):
            return

        inv = inv_resp.json()["items"][0]

        self.client.post(
            f"{BASE_URL}/wms/inventory/movements",
            json={
                "product_id": inv["product_id"],
                "warehouse_id": inv["warehouse_id"],
                "movement_type": "in",
                "quantity": str(random.randint(10, 100)),
                "notes": "Load test stock movement",
            },
            name="POST /wms/inventory/movements",
        )

    @task(1)
    def update_batch_status(self):
        """Update a production batch status."""
        batches_resp = self.client.get(
            f"{BASE_URL}/erp/batches?status=planned&page_size=3",
            name="GET /erp/batches (for update)",
        )
        if batches_resp.status_code != 200 or not batches_resp.json().get("items"):
            return

        batch = batches_resp.json()["items"][0]
        self.client.patch(
            f"{BASE_URL}/erp/batches/{batch['id']}",
            json={"status": "in_progress"},
            name="PATCH /erp/batches/:id",
        )

    @task(1)
    def view_customer_analytics(self):
        """View customer analytics."""
        customers_resp = self.client.get(
            f"{BASE_URL}/crm/customers?page=1&page_size=3",
            name="GET /crm/customers (for analytics)",
        )
        if customers_resp.status_code == 200 and customers_resp.json().get("items"):
            customer_id = customers_resp.json()["items"][0]["id"]
            self.client.get(
                f"{BASE_URL}/crm/customers/{customer_id}/analytics",
                name="GET /crm/customers/:id/analytics",
            )


# ─── Load Test Scenarios ──────────────────────────────────────────────────────
"""
SCENARIO 1 — Baseline (100 users):
    locust -f locustfile.py --host=http://localhost:80 \
           --users 100 --spawn-rate 10 --run-time 5m --headless \
           --csv=results/baseline

Expected:
    - Response time p50 < 200ms
    - Response time p95 < 500ms
    - Error rate < 1%
    - RPS: ~50-100

SCENARIO 2 — Moderate Load (500 users):
    locust -f locustfile.py --host=https://sweetfactory.com \
           --users 500 --spawn-rate 20 --run-time 10m --headless \
           --csv=results/moderate

Expected (with Auto Scaling):
    - Auto Scaling triggers at CPU > 70% (2→4 instances)
    - Response time p50 < 300ms
    - Response time p95 < 800ms
    - Error rate < 2%

SCENARIO 3 — High Load (1000 users):
    locust -f locustfile.py --host=https://sweetfactory.com \
           --users 1000 --spawn-rate 30 --run-time 10m --headless \
           --csv=results/high_load

Expected (with Auto Scaling):
    - Auto Scaling triggers further (4→8 instances)
    - Response time p50 < 500ms
    - Response time p95 < 1500ms
    - Error rate < 5%

SCENARIO 4 — Stress Test (2000 users):
    locust -f locustfile.py --host=https://sweetfactory.com \
           --users 2000 --spawn-rate 50 --run-time 15m --headless \
           --csv=results/stress

Expected (system limits):
    - Max instances reached (10)
    - Response time degrades gracefully
    - No service crashes
    - Errors expected when at capacity
"""
