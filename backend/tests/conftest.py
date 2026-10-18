import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole

# In-memory SQLite async test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client with overridden database dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def test_users(db_session: AsyncSession):
    """Seed test users with all 4 mandatory roles."""
    users = {
        "admin": User(
            id="user-admin-1",
            username="admin_test",
            email="admin@test.com",
            full_name="Admin Test",
            role=UserRole.ADMINISTRATOR,
            hashed_password=hash_password("AdminPass123!"),
            is_active=True
        ),
        "engineer": User(
            id="user-eng-1",
            username="eng_test",
            email="eng@test.com",
            full_name="Engineer Test",
            role=UserRole.ENGINEER,
            hashed_password=hash_password("EngineerPass123!"),
            is_active=True
        ),
        "tech_lead": User(
            id="user-lead-1",
            username="lead_test",
            email="lead@test.com",
            full_name="Lead Test",
            role=UserRole.TECHNICAL_LEAD,
            hashed_password=hash_password("LeadPass123!"),
            is_active=True
        ),
        "final_validator": User(
            id="user-val-1",
            username="val_test",
            email="val@test.com",
            full_name="Validator Test",
            role=UserRole.FINAL_VALIDATOR,
            hashed_password=hash_password("ValPass123!"),
            is_active=True
        ),
        "inactive": User(
            id="user-inact-1",
            username="inactive_test",
            email="inactive@test.com",
            full_name="Inactive User",
            role=UserRole.ENGINEER,
            hashed_password=hash_password("InactivePass123!"),
            is_active=False
        )
    }
    for u in users.values():
        db_session.add(u)
    await db_session.commit()
    return users

@pytest.fixture
def auth_tokens(test_users):
    """Generate valid JWT tokens for each seeded role."""
    return {
        role: create_access_token(
            data={"sub": user.id, "username": user.username, "role": user.role.value}
        )
        for role, user in test_users.items()
    }
