"""Shared FastAPI dependencies: DB session, current user, owned project."""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationException, PermissionException
from app.core.security import decode_token
from app.models.project import Project
from app.models.user import User
from app.repositories.repositories import ProjectRepository, UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationException("Missing bearer token")
    payload = decode_token(credentials.credentials, expected_type="access")
    user = UserRepository(db).get(payload["sub"])
    if not user or not user.active:
        raise AuthenticationException("User not found or disabled")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise PermissionException("Admin privileges required")
    return user


def get_owned_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """Resolve a project from the path and assert ownership."""
    project = ProjectRepository(db).get(project_id)
    if not project:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("Project not found")
    if project.user_id != user.id and not user.is_admin:
        raise PermissionException("You do not own this project")
    return project
