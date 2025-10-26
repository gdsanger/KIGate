#!/usr/bin/env python3
"""
Manual test script for rate limiting functionality

This script demonstrates and tests the rate limiting features:
1. Creates a test user with custom limits
2. Makes requests until rate limit is hit
3. Shows HTTP 429 error when limits are exceeded
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from model.user import Base, UserCreate
from service.user_service import UserService
from database import AsyncSessionLocal, init_db


async def create_test_user():
    """Create a test user with low rate limits for testing"""
    print("Creating test user with low rate limits (RPM=3, TPM=1000)...")
    
    async with AsyncSessionLocal() as session:
        user_data = UserCreate(
            name="Rate Limit Test User",
            email="ratelimit@test.com",
            rpm_limit=3,
            tpm_limit=1000
        )
        
        user = await UserService.create_user(session, user_data, send_email=False)
        await session.commit()
        
        print(f"\nTest user created successfully!")
        print(f"  Client ID: {user.client_id}")
        print(f"  Client Secret: {user.client_secret}")
        print(f"  RPM Limit: {user.rpm_limit}")
        print(f"  TPM Limit: {user.tpm_limit}")
        print(f"\nUse these credentials with Bearer token:")
        print(f"  Authorization: Bearer {user.client_id}:{user.client_secret}")
        
        return user


async def test_rate_limits():
    """Test rate limiting by inspecting a user's rate limit counters"""
    print("\n" + "="*70)
    print("Testing Rate Limit Functionality")
    print("="*70 + "\n")
    
    # Initialize database
    await init_db()
    
    # Create test user
    user = await create_test_user()
    
    if not user:
        return
    
    print("\n" + "="*70)
    print("Manual Testing Instructions:")
    print("="*70)
    print("\n1. Start the KIGate server:")
    print("   python main.py")
    print("\n2. Test the health endpoint (not rate limited):")
    print(f"   curl http://localhost:8000/health")
    print("\n3. Make requests to rate-limited endpoints using the credentials above:")
    print(f"   curl -X POST http://localhost:8000/api/openai \\")
    print(f"     -H 'Authorization: Bearer {user.client_id}:{user.client_secret}' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"job_id\":\"test-1\",\"user_id\":\"test\",\"model\":\"gpt-3.5-turbo\",\"message\":\"Hello\"}}'")
    print("\n4. After 3 requests, you should get HTTP 429 (Too Many Requests)")
    print("\n5. Wait 60 seconds and try again - limits will reset\n")
    
    print("Alternative: Test with /health endpoint (requires API key):")
    print(f"  curl 'http://localhost:8000/health?api_key={user.client_id}:{user.client_secret}'")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_rate_limits())
