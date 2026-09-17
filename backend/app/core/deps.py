from fastapi import Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import User


async def require_demo_routes() -> None:
    """Guard for fixtures and throwaway accounts. Off by default outside development."""
    if not get_settings().enable_demo_routes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )


class UserScope:
    """Carries the authenticated user alongside the session so that tenant scoping is
    something a handler has to actively discard rather than remember to add."""

    __slots__ = ("user", "db")

    def __init__(self, user: User, db: AsyncSession) -> None:
        self.user = user
        self.db = db

    @property
    def user_id(self) -> int:
        return self.user.id

    def scope(self, stmt: Select, model) -> Select:
        return stmt.where(model.user_id == self.user.id)


async def get_scope(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserScope:
    return UserScope(user=user, db=db)
