"""
Sweet Factory ERP — Authentication Service
Business logic for user authentication and token management.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.core.config import settings
from app.models.models import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse


class AuthService:
    """Handles all authentication business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        """
        Authenticate user with email/password.
        Returns JWT access + refresh tokens.
        """
        user = await self.user_repo.get_by_email(credentials.email)

        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact administrator.",
            )

        await self.user_repo.update_last_login(user.id)

        access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Exchange a valid refresh token for new access token."""
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user_id = UUID(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )

        access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register_user(self, data: UserCreate) -> UserResponse:
        """Register a new user (admin only in production)."""
        # Check uniqueness
        existing_email = await self.user_repo.get_by_email(data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        existing_username = await self.user_repo.get_by_username(data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

        # Validate role
        try:
            role = UserRole(data.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Choose from: {[r.value for r in UserRole]}",
            )

        user = User(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=role,
            is_active=True,
            is_verified=False,
        )
        created = await self.user_repo.create(user)
        return UserResponse.model_validate(created)

    async def get_current_user(self, user_id: UUID) -> User:
        """Fetch currently authenticated user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
