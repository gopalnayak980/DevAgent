"""
Phase 10.2 — User Repository.

Data access layer for the User model. All database interactions go through
this repository. The service layer handles business logic.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        """Persist a new user."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a user by primary key."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by normalized email address."""
        result = await self.session.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return result.scalar_one_or_none()

    async def update(self, user: User) -> User:
        """Persist updates to an existing user."""
        await self.session.commit()
        await self.session.refresh(user)
        return user
