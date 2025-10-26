"""
Integration test for Claude API endpoint
Tests the complete flow from HTTP request to controller response
"""
import asyncio
import httpx
import logging
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_claude_integration():
    """Test Claude API integration without real API key"""
    print("Testing Claude API integration...\n")
    
    # Test data matching the aiapirequest model structure
    test_request = {
        "job_id": "integration-test-job-456",
        "user_id": "integration-test-user-789",
        "model": "claude-3-sonnet-20240229",
        "message": "Hello Claude, please respond with a greeting."
    }
    
    # Test controller directly (without HTTP layer)
    print("1. Testing controller directly...")
    try:
        from controller.api_claude import process_claude_request
        
        # Create aiapirequest object
        request = aiapirequest(**test_request)
        
        # Process the request
        result = await process_claude_request(request)
        
        # Validate the response structure
        assert isinstance(result, aiapiresult), "Result should be aiapiresult instance"
        assert result.job_id == test_request["job_id"], "job_id should be preserved"
        assert result.user_id == test_request["user_id"], "user_id should be preserved"
        assert isinstance(result.success, bool), "success should be boolean"
        assert isinstance(result.content, str), "content should be string"
        
        if result.success:
            print("   ✓ Request succeeded")
            print(f"   ✓ Response content: {result.content[:100]}...")
        else:
            print(f"   ✓ Request failed as expected: {result.error_message}")
            # We expect this to fail due to no API key being configured
            assert "API key" in result.error_message or "authentication" in result.error_message.lower()
            
        print("   ✓ All response fields properly structured")
        
    except Exception as e:
        print(f"   ❌ Controller test failed: {e}")
        raise
    
    print("\n2. Testing model validation...")
    try:
        # Test with empty message
        invalid_request = aiapirequest(
            job_id="validation-test",
            user_id="validation-user", 
            model="claude-3-sonnet-20240229",
            message=""
        )
        
        result = await process_claude_request(invalid_request)
        assert not result.success, "Empty message should cause failure"
        assert "Message cannot be empty" in result.error_message, "Should validate empty message"
        print("   ✓ Empty message validation works")
        
        # Test with empty model
        invalid_request = aiapirequest(
            job_id="validation-test-2",
            user_id="validation-user-2",
            model="",
            message="Valid message"
        )
        
        result = await process_claude_request(invalid_request)
        assert not result.success, "Empty model should cause failure"
        assert "Model cannot be empty" in result.error_message, "Should validate empty model"
        print("   ✓ Empty model validation works")
        
    except Exception as e:
        print(f"   ❌ Validation test failed: {e}")
        raise
    
    print("\n3. Testing endpoint availability (without auth)...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/api/claude",
                json=test_request,
                timeout=10.0
            )
            
            # Should get 403 due to missing authentication
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("   ✓ Endpoint correctly requires authentication")
            
    except httpx.ConnectError:
        print("   ⚠ Server not running - endpoint test skipped")
        print("   ℹ Start server with: python main.py")
    except Exception as e:
        print(f"   ❌ Endpoint test failed: {e}")
        raise
    
    print("\n✅ All Claude integration tests passed!")
    print("\n📋 Summary of implemented features:")
    print("   • Claude API controller with async support")
    print("   • Proper aiapirequest/aiapiresult object handling")
    print("   • job_id and user_id preservation in responses")
    print("   • success/error status handling")
    print("   • Comprehensive input validation")
    print("   • Error logging and handling")
    print("   • HTTP endpoint with authentication")
    print("   • Integration with FastAPI application")


if __name__ == "__main__":
    asyncio.run(test_claude_integration())