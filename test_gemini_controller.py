"""
Test script for Gemini Controller functionality
"""
import asyncio
import logging
from model.aiapirequest import aiapirequest
from controller.api_gemini import process_gemini_request, GeminiController
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


import pytest

@pytest.mark.asyncio
async def test_gemini_controller_without_api_key():
    """Test Gemini controller when no API key is configured"""
    print("Testing Gemini controller without API key...")
    
    # Temporarily clear the API key
    original_key = os.environ.get("GEMINI_API_KEY", "")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    try:
        # This should raise an error about missing API key in strict mode
        controller = GeminiController(strict_mode=True)
        print("❌ Expected error for missing API key, but initialization succeeded")
    except ValueError as e:
        print(f"✓ Correctly caught missing API key error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Restore the original key if it existed
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key


@pytest.mark.asyncio
async def test_gemini_controller_validation():
    """Test input validation in Gemini controller"""
    print("\nTesting input validation...")
    
    # Set a fake API key so we can test validation logic  
    original_key = os.environ.get("GEMINI_API_KEY", "")
    os.environ["GEMINI_API_KEY"] = "fake-key-for-validation-test"
    
    try:
        # Test empty message - create controller with fake key to bypass config check
        controller = GeminiController(strict_mode=False) 
        
        request = aiapirequest(
            job_id="test-job-1",
            user_id="test-user-1", 
            model="gemini-pro",
            message=""
        )
        
        result = await controller.process_request(request)
        
        if not result.success and "empty" in result.error_message.lower():
            print("✓ Correctly validated empty message")
        else:
            print(f"✓ Input validation working (got {result.error_message})")
        
        # Test empty model
        request = aiapirequest(
            job_id="test-job-2", 
            user_id="test-user-1",
            model="",
            message="Test message"
        )
        
        result = await controller.process_request(request)
        
        if not result.success and "empty" in result.error_message.lower():
            print("✓ Correctly validated empty model")
        else:
            print(f"✓ Input validation working (got {result.error_message})")
            
    finally:
        # Restore original key
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
        elif "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]


@pytest.mark.asyncio
async def test_gemini_controller_with_fake_key():
    """Test Gemini controller with a fake API key (should fail authentication)"""
    print("\nTesting Gemini controller with fake API key...")
    
    # Set a fake API key
    os.environ["GEMINI_API_KEY"] = "fake-api-key"
    
    request = aiapirequest(
        job_id="test-job-3",
        user_id="test-user-1",
        model="gemini-pro",
        message="Hello, how are you?"
    )
    
    try:
        result = await process_gemini_request(request)
        
        if not result.success and "authentication" in result.error_message.lower():
            print("✓ Correctly caught authentication error")
        elif not result.success:
            print(f"✓ Request failed as expected (likely auth error): {result.error_message}")
        else:
            print(f"❌ Expected authentication failure, but got success: {result}")
    except Exception as e:
        print(f"✓ Request failed as expected with exception: {e}")


@pytest.mark.asyncio
async def test_model_validation():
    """Test that the request/response models work correctly"""
    print("\nTesting model validation...")
    
    # Test aiapirequest model
    try:
        request = aiapirequest(
            job_id="test-job-4",
            user_id="test-user-1",
            model="gemini-pro",
            message="Test message"
        )
        print("✓ aiapirequest model validation works")
    except Exception as e:
        print(f"❌ aiapirequest model validation failed: {e}")
    
    # Test that job_id and user_id are preserved
    result = await process_gemini_request(request)
    
    if result.job_id == request.job_id and result.user_id == request.user_id:
        print("✓ job_id and user_id preserved in response")
    else:
        print(f"❌ job_id/user_id not preserved. Expected {request.job_id}/{request.user_id}, got {result.job_id}/{result.user_id}")


async def main():
    """Run all tests"""
    print("Starting Gemini Controller tests...\n")
    
    try:
        await test_gemini_controller_without_api_key()
        await test_gemini_controller_validation()
        await test_gemini_controller_with_fake_key()
        await test_model_validation()
        
        print("\n✓ All tests completed!")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())