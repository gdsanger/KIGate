"""
Integration tests for rate limiting with authentication
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from model.user import User, Base, UserCreate
from service.user_service import UserService


@pytest_asyncio.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_service_creates_users_with_default_limits(test_db):
    """Test that user service creates users with default rate limits"""
    async_session = sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user_data = UserCreate(
            name="New User",
            email="new@example.com"
        )
        
        user = await UserService.create_user(session, user_data, send_email=False)
        await session.commit()
        
        # Verify default limits are set
        assert user.rpm_limit == 20
        assert user.tpm_limit == 50000
        assert user.current_rpm == 0
        assert user.current_tpm == 0


@pytest.mark.asyncio
async def test_user_service_creates_users_with_custom_limits(test_db):
    """Test that user service can create users with custom rate limits"""
    async_session = sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user_data = UserCreate(
            name="Custom User",
            email="custom@example.com",
            rpm_limit=100,
            tpm_limit=200000
        )
        
        user = await UserService.create_user(session, user_data, send_email=False)
        await session.commit()
        
        # Verify custom limits are set
        assert user.rpm_limit == 100
        assert user.tpm_limit == 200000


@pytest.mark.asyncio
async def test_user_rate_limit_increments(test_db):
    """Test that user rate limits increment correctly"""
    async_session = sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user = User(
            client_id="test-client",
            client_secret="test-secret",
            name="Test User",
            email="test@example.com",
            is_active=True,
            rpm_limit=5,
            tpm_limit=1000,
            current_rpm=0,
            current_tpm=0,
            last_reset_time=None
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Test increment_request_count
        assert user.current_rpm == 0
        user.increment_request_count()
        assert user.current_rpm == 1
        
        # Test multiple increments
        user.increment_request_count()
        user.increment_request_count()
        assert user.current_rpm == 3
        
        # Test check_rpm_limit
        assert user.check_rpm_limit() is True
        
        # Reach limit
        user.increment_request_count()
        user.increment_request_count()
        assert user.current_rpm == 5
        assert user.check_rpm_limit() is False


@pytest.mark.asyncio
async def test_rate_limit_reset(test_db):
    """Test that rate limits reset after 1 minute"""
    async_session = sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user = User(
            client_id="test-client",
            client_secret="test-secret",
            name="Test User",
            email="test@example.com",
            is_active=True,
            rpm_limit=5,
            tpm_limit=1000,
            current_rpm=5,
            current_tpm=500,
            last_reset_time=datetime.utcnow() - timedelta(seconds=61)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Counters should be at limit
        assert user.current_rpm == 5
        assert user.current_tpm == 500
        
        # Reset should occur
        user.reset_rate_limits_if_needed()
        
        # Counters should be reset
        assert user.current_rpm == 0
        assert user.current_tpm == 0
        assert user.last_reset_time is not None

