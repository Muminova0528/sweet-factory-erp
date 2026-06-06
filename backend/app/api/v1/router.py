"""
Sweet Factory ERP — API v1 Router
Combines all module routers under /api/v1 prefix.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, erp, crm, wms, dashboard

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(erp.router)
api_router.include_router(crm.router)
api_router.include_router(wms.router)
api_router.include_router(dashboard.router)
