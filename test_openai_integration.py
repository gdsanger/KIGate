"""
Integration test for OpenAI API endpoint
This test demonstrates how to use the OpenAI endpoint via HTTP calls
"""
import asyncio
import httpx
import json
import logging
from database import get_async_session, init_db
from service.user_service import UserService
from model.user import UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def create_test_user():
    """Create a test user and return credentials"""
    print("Creating test user for API authentication...")
    
    await init_db()
    
    async for db in get_async_session():
        # Create a test user
        user_data = UserCreate(
            name="OpenAI Test User",
            email="openai-test@example.com",
            is_active=True
        )
        
        user = await UserService.create_user(db, user_data)
        user_with_secret = await UserService.get_user_with_secret(db, user.client_id)
        await db.commit()
        
        print(f"✓ Created test user: {user.name}")
        print(f"  Client ID: {user.client_id}")
        print(f"  Client Secret: {user_with_secret.client_secret}")
        
        return user_with_secret


async def test_openai_endpoint():
    """Test the OpenAI API endpoint"""
    print("\nTesting OpenAI API endpoint...")
    
    # Get test user credentials
    test_user = await create_test_user()
    api_key = f"{test_user.client_id}:{test_user.client_secret}"
    
    async with httpx.AsyncClient() as client:
        # Test the OpenAI endpoint
        request_data = {
            "job_id": "test-job-12345",
            "user_id": "test-user-67890", 
            "model": "gpt-3.5-turbo",
            "role": "user",
            "prompt": "Hello, please respond with 'Test successful' if you can read this."
        }
        
        # Note: This will likely fail due to no valid OpenAI API key being configured,
        # but it demonstrates the endpoint structure and error handling
        try:
            response = await client.post(
                f"{BASE_URL}/api/openai",
                json=request_data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Request successful!")
                print(f"  Job ID: {result['job_id']}")
                print(f"  User ID: {result['user_id']}")
                print(f"  Success: {result['success']}")
                if result['success']:
                    print(f"  Content: {result['content']}")
                else:
                    print(f"  Error: {result['error_message']}")
                    
                # Verify job_id and user_id are preserved
                if (result['job_id'] == request_data['job_id'] and 
                    result['user_id'] == request_data['user_id']):
                    print("✓ Job ID and User ID correctly preserved")
                else:
                    print("❌ Job ID and User ID not preserved correctly")
                    
            elif response.status_code == 401:
                print("❌ Authentication failed - check API key")
            elif response.status_code == 422:
                print("❌ Validation error:")
                print(response.text)
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(response.text)
                
        except httpx.ConnectError:
            print("❌ Could not connect to server. Make sure the server is running with:")
            print("   python main.py")
        except Exception as e:
            print(f"❌ Request failed: {e}")


async def test_validation_errors():
    """Test validation errors through the API"""
    print("\nTesting validation errors...")
    
    # Get test user credentials (reuse the existing one if possible)
    async for db in get_async_session():
        users = await UserService.get_users(db, limit=1)
        if users:
            test_user = await UserService.get_user_with_secret(db, users[0].client_id)
            api_key = f"{test_user.client_id}:{test_user.client_secret}"
            break
    else:
        test_user = await create_test_user()
        api_key = f"{test_user.client_id}:{test_user.client_secret}"
    
    async with httpx.AsyncClient() as client:
        # Test empty prompt
        request_data = {
            "job_id": "test-validation-1",
            "user_id": "test-user-1",
            "model": "gpt-3.5-turbo",
            "role": "user",
            "prompt": ""  # Empty prompt should be rejected
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/openai",
                json=request_data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if not result['success'] and 'empty' in result['error_message'].lower():
                    print("✓ Empty prompt validation works correctly")
                elif not result['success']:
                    print(f"✓ Request failed as expected: {result['error_message']}")
                else:
                    print("❌ Expected validation error for empty prompt")
            else:
                print(f"❌ Unexpected status code for validation test: {response.status_code}")
                
        except httpx.ConnectError:
            print("❌ Could not connect to server")
        except Exception as e:
            print(f"❌ Validation test failed: {e}")


async def main():
    """Run integration tests"""
    print("=== OpenAI API Integration Tests ===")
    print("Note: These tests require a running server (python main.py)")
    print("The actual OpenAI API calls may fail without a valid API key,")
    print("but the endpoint structure and error handling will be tested.\n")
    
    try:
        await test_openai_endpoint()
        await test_validation_errors()
        
        print("\n=== Integration Tests Complete ===")
        print("To test with actual OpenAI API:")
        print("1. Set OPENAI_API_KEY in your .env file")
        print("2. Run: python main.py")
        print("3. Run this test script in another terminal")
        
    except Exception as e:
        print(f"\n❌ Integration tests failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())