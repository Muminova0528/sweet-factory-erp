"""
Sweet Factory Cloud ERP Platform
Main FastAPI application entry point.

Architecture: Clean Architecture with Repository Pattern
BTEC Unit 6: Networking in the Cloud — Learning Aims A, B, C, D
"""
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, Base

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("sweet_factory")


# ─── Lifespan (startup/shutdown) ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown events."""
    logger.info("🍬 Sweet Factory ERP starting up...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")

    # Create tables in development (use Alembic in production)
    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified")

    yield

    logger.info("🛑 Sweet Factory ERP shutting down...")
    await engine.dispose()


# ─── FastAPI Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="Sweet Factory Cloud ERP",
    description="""
## 🍬 Sweet Factory Cloud ERP Platform

A comprehensive cloud-native ERP system for confectionery manufacturing.

### Modules
- **ERP**: Production management, batch tracking, ingredient control
- **CRM**: Customer management, order processing, distributor tracking
- **WMS**: Warehouse management, inventory control, shipment tracking
- **Dashboard**: Real-time KPIs and analytics

### Authentication
All endpoints (except `/auth/login`) require a Bearer JWT token.
Get your token from `POST /api/v1/auth/login`.

### BTEC Unit 6 Coverage
This platform demonstrates all networking concepts required for 
Learning Aims A, B, C, and D of BTEC Unit 6: Networking in the Cloud.
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-App-Version"] = settings.APP_VERSION
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"← {request.method} {request.url.path} [{response.status_code}]")
    return response


# ─── Global Exception Handlers ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please contact support.",
            "path": str(request.url.path),
        },
    )


# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/", tags=["Health"])
async def root():
    """Platform info and health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "modules": ["auth", "erp", "crm", "wms", "dashboard"],
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint — used by ALB target group health checks."""
    from sqlalchemy import text
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": settings.APP_VERSION,
    }


@app.get("/metrics", tags=["Health"])
async def metrics():
    """Basic metrics endpoint for monitoring."""
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "version": settings.APP_VERSION,
    }
