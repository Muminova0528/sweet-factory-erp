"""
Sweet Factory ERP — Integration Tests
Tests full request/response cycle via FastAPI test client.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.models import User, UserRole

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/sweet_factory_test"


# ─── Test Database Setup ──────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_session):
    """HTTP client with overridden DB dependency."""
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(test_session: AsyncSession):
    """Create a test admin user."""
    user = User(
        email="admin@test.com",
        username="admin_test",
        full_name="Test Admin",
        hashed_password=hash_password("Admin@Test123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    """Get JWT token for admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin@Test123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Auth Endpoint Tests ───────────────────────────────────────────────────────
class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(self, client, admin_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "Admin@Test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_credentials(self, client, admin_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "WrongPass@999"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me(self, client, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_protected_route_without_token(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403  # HTTPBearer raises 403 when no credentials

    @pytest.mark.asyncio
    async def test_protected_route_invalid_token(self, client):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_user(self, client, auth_headers):
        response = await client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={
                "email": "newstaff@test.com",
                "username": "newstaff",
                "full_name": "New Staff Member",
                "password": "StaffPass@123",
                "role": "employee",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newstaff@test.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, auth_headers, admin_user):
        response = await client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={
                "email": "admin@test.com",  # Already exists
                "username": "another_admin",
                "full_name": "Duplicate Admin",
                "password": "Admin@Test123",
                "role": "admin",
            },
        )
        assert response.status_code == 409


# ─── ERP Endpoint Tests ───────────────────────────────────────────────────────
class TestERPEndpoints:
    @pytest.mark.asyncio
    async def test_create_product(self, client, auth_headers):
        response = await client.post(
            "/api/v1/erp/products",
            headers=auth_headers,
            json={
                "sku": "CAKE-001",
                "name": "Chocolate Birthday Cake",
                "description": "Premium chocolate cake",
                "category": "cake",
                "unit": "piece",
                "unit_price": "45.00",
                "cost_price": "18.00",
                "weight_grams": 1200,
                "shelf_life_days": 5,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "CAKE-001"
        assert data["name"] == "Chocolate Birthday Cake"

    @pytest.mark.asyncio
    async def test_create_duplicate_sku(self, client, auth_headers):
        # Create first product
        await client.post(
            "/api/v1/erp/products",
            headers=auth_headers,
            json={
                "sku": "CHOC-DUP",
                "name": "Chocolate Bar",
                "category": "chocolate",
                "unit": "piece",
                "unit_price": "5.00",
                "cost_price": "2.00",
            },
        )
        # Try to create with same SKU
        response = await client.post(
            "/api/v1/erp/products",
            headers=auth_headers,
            json={
                "sku": "CHOC-DUP",
                "name": "Another Product",
                "category": "chocolate",
                "unit": "piece",
                "unit_price": "5.00",
                "cost_price": "2.00",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_products(self, client, auth_headers):
        response = await client.get("/api/v1/erp/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data


# ─── CRM Endpoint Tests ───────────────────────────────────────────────────────
class TestCRMEndpoints:
    @pytest.mark.asyncio
    async def test_create_customer(self, client, auth_headers):
        response = await client.post(
            "/api/v1/crm/customers",
            headers=auth_headers,
            json={
                "company_name": "Tashkent Supermarket",
                "contact_name": "Alisher Karimov",
                "email": "alisher@tashkent-market.uz",
                "phone": "+998901234567",
                "city": "Tashkent",
                "country": "Uzbekistan",
                "credit_limit": "5000.00",
                "is_distributor": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Tashkent Supermarket"

    @pytest.mark.asyncio
    async def test_list_customers(self, client, auth_headers):
        response = await client.get("/api/v1/crm/customers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


# ─── Health Check Tests ───────────────────────────────────────────────────────
class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
