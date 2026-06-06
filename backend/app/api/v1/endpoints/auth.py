"""
Sweet Factory ERP — Auth API Endpoints
POST /auth/login
POST /auth/refresh
POST /auth/register
GET  /auth/me
POST /auth/logout
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.models import User, UserRole
from app.schemas.schemas import (
    LoginRequest, TokenResponse, RefreshTokenRequest,
    UserCreate, UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return JWT access + refresh tokens."""
    service = AuthService(db)
    return await service.login(credentials)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    service = AuthService(db)
    return await service.refresh_access_token(body.refresh_token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Admin only)",
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserResponse:
    """Create a new platform user. Requires admin role."""
    service = AuthService(db)
    return await service.register_user(data)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (client-side token invalidation)",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Logout endpoint. Since JWTs are stateless, actual invalidation
    is handled client-side by discarding the token.
    In production, implement a token blacklist using Redis.
    """
    return {
        "message": f"User {current_user.email} logged out successfully",
        "instruction": "Discard your access and refresh tokens.",
    }
