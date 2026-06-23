"""Authentication and user-profile business logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException, ConflictException, NotFoundException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.repositories import (
    RefreshTokenRepository,
    UserRepository,
    UserSettingsRepository,
)
from app.schemas.auth import ProfileUpdate, RegisterRequest


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)
        self.settings_repo = UserSettingsRepository(db)

    def register(self, payload: RegisterRequest) -> tuple[User, str, str]:
        email = payload.email.lower().strip()
        if self.users.get_by_email(email):
            raise ConflictException("Email already registered")
        is_first = self.users.count() == 0
        user = self.users.create(
            email=email,
            password_hash=hash_password(payload.password),
            name=payload.name.strip(),
            is_admin=is_first,  # first registered user becomes admin
        )
        self.settings_repo.create(user_id=user.id)
        access, refresh = self._issue_tokens(user)
        self.db.commit()
        return user, access, refresh

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.users.get_by_email(email.lower().strip())
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationException("Invalid email or password")
        if not user.active:
            raise AuthenticationException("Account is disabled")
        user.last_login_at = datetime.now(timezone.utc)
        access, refresh = self._issue_tokens(user)
        self.db.commit()
        return user, access, refresh

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        stored = self.tokens.get_active(refresh_token)
        if not stored:
            raise AuthenticationException("Refresh token revoked or unknown")
        user = self.users.get(payload["sub"])
        if not user or not user.active:
            raise AuthenticationException("User not found or disabled")
        stored.revoked = True
        access, refresh = self._issue_tokens(user)
        self.db.commit()
        return access, refresh

    def logout(self, user_id: str) -> None:
        self.tokens.revoke_all(user_id)
        self.db.commit()

    def change_password(self, user: User, old_password: str, new_password: str) -> None:
        if not verify_password(old_password, user.password_hash):
            raise AuthenticationException("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        self.tokens.revoke_all(user.id)
        self.db.commit()

    def update_profile(self, user: User, payload: ProfileUpdate) -> User:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user(self, user_id: str) -> User:
        user = self.users.get(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    def _issue_tokens(self, user: User) -> tuple[str, str]:
        access = create_access_token(user.id, extra={"email": user.email, "admin": user.is_admin})
        refresh = create_refresh_token(user.id)
        expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.tokens.create(user_id=user.id, token=refresh, expires_at=expires)
        return access, refresh
