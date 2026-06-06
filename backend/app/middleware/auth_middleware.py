"""
Sweet Factory ERP — Authentication Middleware
FastAPI dependencies for JWT authentication and RBAC.
"""
from typing import Optional, Set
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.models import User, UserRole
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: validates Bearer JWT token, returns current user.
    Raises 401 if token is invalid/expired.
    """
    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias for get_current_user — ensures user is active."""
    return current_user


def require_roles(*allowed_roles: UserRole):
    """
    Role-based access control decorator factory.

    Usage:
        @router.get("/admin")
        async def admin_only(user = Depends(require_roles(UserRole.ADMIN))):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


# Pre-built role dependencies
require_admin = require_roles(UserRole.ADMIN)
require_production = require_roles(UserRole.ADMIN, UserRole.PRODUCTION_MANAGER)
require_warehouse = require_roles(UserRole.ADMIN, UserRole.WAREHOUSE_MANAGER)
require_sales = require_roles(UserRole.ADMIN, UserRole.SALES_MANAGER)
require_manager = require_roles(
    UserRole.ADMIN,
    UserRole.PRODUCTION_MANAGER,
    UserRole.WAREHOUSE_MANAGER,
    UserRole.SALES_MANAGER,
)
