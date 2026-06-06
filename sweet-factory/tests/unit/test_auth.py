"""
Sweet Factory ERP — Unit Tests: Auth Service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import User, UserRole
from app.schemas.schemas import LoginRequest, UserCreate
from app.services.auth_service import AuthService


# ─── Security Utilities Tests ─────────────────────────────────────────────────
class TestPasswordHashing:
    def test_hash_password_returns_bcrypt_hash(self):
        plain = "SecretPass@123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        plain = "SecretPass@123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("CorrectPass@123")
        assert verify_password("WrongPass@123", hashed) is False

    def test_different_passwords_different_hashes(self):
        p1 = hash_password("Pass@123")
        p2 = hash_password("Pass@123")
        # bcrypt uses salt — same input produces different hashes
        assert p1 != p2


class TestJWTTokens:
    def test_create_access_token(self):
        user_id = uuid4()
        token = create_access_token(subject=str(user_id), role="admin")
        assert isinstance(token, str)
        assert len(token) > 50

    def test_access_token_payload(self):
        from app.core.security import decode_token
        user_id = uuid4()
        token = create_access_token(subject=str(user_id), role="sales_manager")
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["role"] == "sales_manager"
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        from jose import JWTError
        from app.core.security import decode_token
        # Manually create an expired token
        from datetime import datetime, timezone, timedelta
        from jose import jwt
        from app.core.config import settings

        expired_payload = {
            "sub": str(uuid4()),
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(JWTError):
            decode_token(expired_token)


# ─── Auth Service Tests ───────────────────────────────────────────────────────
class TestAuthService:
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@sweetfactory.com"
        user.username = "testuser"
        user.full_name = "Test User"
        user.hashed_password = hash_password("TestPass@123")
        user.role = UserRole.EMPLOYEE
        user.is_active = True
        user.is_verified = True
        return user

    @pytest.mark.asyncio
    async def test_login_success(self, mock_session, mock_user):
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_repo.update_last_login = AsyncMock()

            service = AuthService(mock_session)
            result = await service.login(
                LoginRequest(email="test@sweetfactory.com", password="TestPass@123")
            )

            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_session, mock_user):
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)

            service = AuthService(mock_session)
            with pytest.raises(HTTPException) as exc_info:
                await service.login(
                    LoginRequest(email="test@sweetfactory.com", password="WrongPass@999")
                )
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_session):
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=None)

            service = AuthService(mock_session)
            with pytest.raises(HTTPException) as exc_info:
                await service.login(
                    LoginRequest(email="nobody@sweetfactory.com", password="AnyPass@123")
                )
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, mock_session, mock_user):
        mock_user.is_active = False
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)

            service = AuthService(mock_session)
            with pytest.raises(HTTPException) as exc_info:
                await service.login(
                    LoginRequest(email="test@sweetfactory.com", password="TestPass@123")
                )
            assert exc_info.value.status_code == 403


# ─── Schema Validation Tests ──────────────────────────────────────────────────
class TestUserCreateSchema:
    def test_valid_user_create(self):
        data = UserCreate(
            email="new@sweetfactory.com",
            username="newuser",
            full_name="New User",
            password="Valid@Pass123",
            role="employee",
        )
        assert data.email == "new@sweetfactory.com"

    def test_password_too_short(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@sf.com",
                username="user",
                full_name="Test",
                password="short",
            )

    def test_password_missing_uppercase(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@sf.com",
                username="user",
                full_name="Test",
                password="allowercase@123",
            )

    def test_password_missing_digit(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@sf.com",
                username="user",
                full_name="Test",
                password="NoDigitHere@ABC",
            )

    def test_invalid_email(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                username="user",
                full_name="Test",
                password="Valid@Pass123",
            )
