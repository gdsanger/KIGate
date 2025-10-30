"""
Tests for rate limiting functionality
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from model.user import User, Base
from service.rate_limit_service import RateLimitService


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory database session for testing"""
    # Create in-memory SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user"""
    user = User(
        client_id="test-client-id",
        client_secret="test-secret",
        name="Test User",
        email="test@example.com",
        is_active=True,
        rpm_limit=5,  # Low limit for testing
        tpm_limit=100,  # Low limit for testing
        current_rpm=0,
        current_tpm=0,
        last_reset_time=None
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_rate_limit_check_within_limits(db_session, test_user):
    """Test that rate limit check passes when within limits"""
    is_allowed, error_message = await RateLimitService.check_rate_limits(
        db_session, test_user, estimated_tokens=10
    )
    
    assert is_allowed is True
    assert error_message is None


@pytest.mark.asyncio
async def test_rate_limit_rpm_exceeded(db_session, test_user):
    """Test that rate limit check fails when RPM limit is exceeded"""
    # Set current RPM to the limit
    test_user.current_rpm = test_user.rpm_limit
    test_user.last_reset_time = datetime.utcnow()
    await db_session.commit()
    
    is_allowed, error_message = await RateLimitService.check_rate_limits(
        db_session, test_user
    )
    
    assert is_allowed is False
    assert "Rate limit exceeded" in error_message


@pytest.mark.asyncio
async def test_rate_limit_tpm_exceeded(db_session, test_user):
    """Test that rate limit check fails when TPM limit would be exceeded"""
    # Set current TPM close to limit
    test_user.current_tpm = 90
    test_user.last_reset_time = datetime.utcnow()
    await db_session.commit()
    
    # Try to add 20 tokens (would exceed 100 limit)
    is_allowed, error_message = await RateLimitService.check_rate_limits(
        db_session, test_user, estimated_tokens=20
    )
    
    assert is_allowed is False
    assert "Token limit exceeded" in error_message


@pytest.mark.asyncio
async def test_rate_limit_reset_after_minute(db_session, test_user):
    """Test that rate limits reset after one minute"""
    # Set current usage to limit with old timestamp
    test_user.current_rpm = test_user.rpm_limit
    test_user.current_tpm = test_user.tpm_limit
    test_user.last_reset_time = datetime.utcnow() - timedelta(seconds=61)
    await db_session.commit()
    
    # Check should pass because limits reset
    is_allowed, error_message = await RateLimitService.check_rate_limits(
        db_session, test_user
    )
    
    assert is_allowed is True
    assert error_message is None
    # Verify counters were reset
    assert test_user.current_rpm == 0
    assert test_user.current_tpm == 0


@pytest.mark.asyncio
async def test_record_request(db_session, test_user):
    """Test recording a request increments counters"""
    initial_rpm = test_user.current_rpm
    initial_tpm = test_user.current_tpm
    
    await RateLimitService.record_request(db_session, test_user, tokens_used=10)
    
    assert test_user.current_rpm == initial_rpm + 1
    assert test_user.current_tpm == initial_tpm + 10


@pytest.mark.asyncio
async def test_multiple_requests_within_limit(db_session, test_user):
    """Test multiple requests within limits"""
    for i in range(3):
        is_allowed, error_message = await RateLimitService.check_rate_limits(
            db_session, test_user, estimated_tokens=10
        )
        assert is_allowed is True
        
        await RateLimitService.record_request(db_session, test_user, tokens_used=10)
    
    # Should still be within limits
    assert test_user.current_rpm == 3
    assert test_user.current_tpm == 30


@pytest.mark.asyncio
async def test_estimate_tokens():
    """Test token estimation"""
    # Test with empty string
    assert RateLimitService.estimate_tokens("") == 0
    
    # Test with short string (4 chars = 1 token)
    assert RateLimitService.estimate_tokens("test") == 1
    
    # Test with longer string (400 chars = 100 tokens)
    long_text = "x" * 400
    assert RateLimitService.estimate_tokens(long_text) == 100


@pytest.mark.asyncio
async def test_user_methods():
    """Test User model rate limiting methods"""
    user = User(
        client_id="test",
        client_secret="secret",
        name="Test",
        rpm_limit=10,
        tpm_limit=100,
        current_rpm=5,
        current_tpm=50,
        last_reset_time=datetime.utcnow()
    )
    
    # Test check_rpm_limit
    assert user.check_rpm_limit() is True
    
    # Test check_tpm_limit
    assert user.check_tpm_limit(30) is True
    assert user.check_tpm_limit(60) is False
    
    # Test increment_request_count
    user.increment_request_count()
    assert user.current_rpm == 6
    
    # Test add_token_usage
    user.add_token_usage(20)
    assert user.current_tpm == 70


@pytest.mark.asyncio
async def test_rate_limit_reset_on_first_use():
    """Test that rate limits initialize correctly on first use"""
    user = User(
        client_id="test",
        client_secret="secret",
        name="Test",
        rpm_limit=10,
        tpm_limit=100,
        current_rpm=0,
        current_tpm=0,
        last_reset_time=None  # First use
    )
    
    # Should initialize reset time and keep counters at 0
    user.reset_rate_limits_if_needed()
    
    assert user.last_reset_time is not None
    assert user.current_rpm == 0
    assert user.current_tpm == 0
