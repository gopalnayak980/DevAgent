import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.models import Base, User
from app.database.session import get_db
from app.auth.dependencies import get_current_active_user, require_admin
from app.main import app
from typing import AsyncGenerator

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async def override_get_db():
        async with TestSession() as session:
            yield session
            
    app.dependency_overrides[get_db] = override_get_db
    
    # Pre-populate a test user for existing tests
    test_user = User(
        id="test-user-id",
        email="test@example.com",
        password_hash="fake_hash",
        name="Test User",
        role="admin",
        is_active=True
    )
    async with TestSession() as session:
        session.add(test_user)
        await session.commit()
    
    async def override_get_user():
        return test_user
        
    app.dependency_overrides[get_current_active_user] = override_get_user
    app.dependency_overrides[require_admin] = override_get_user
    
    async with TestSession() as session:
        yield session
    
    app.dependency_overrides.clear()

