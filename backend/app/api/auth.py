"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import ok
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    _, access, refresh = AuthService(db).register(payload)
    return ok(TokenPair(access_token=access, refresh_token=refresh).model_dump(), "Registered")


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    _, access, refresh = AuthService(db).login(payload.email, payload.password)
    return ok(TokenPair(access_token=access, refresh_token=refresh).model_dump(), "Logged in")


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    access, refresh_token = AuthService(db).refresh(payload.refresh_token)
    return ok(TokenPair(access_token=access, refresh_token=refresh_token).model_dump())


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    AuthService(db).logout(user.id)
    return ok(message="Logged out")


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService(db).change_password(user, payload.old_password, payload.new_password)
    return ok(message="Password changed")


@router.get("/profile")
def profile(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user).model_dump())


@router.put("/profile")
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = AuthService(db).update_profile(user, payload)
    return ok(UserOut.model_validate(updated).model_dump(), "Profile updated")
