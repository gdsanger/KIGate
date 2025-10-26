"""
Test script for Claude Controller functionality
"""
import asyncio
import logging
from model.aiapirequest import aiapirequest
from controller.api_claude import process_claude_request, ClaudeController
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_claude_controller_without_api_key():
    """Test Claude controller when no API key is configured"""
    print("Testing Claude controller without API key...")
    
    # Temporarily clear the API key
    original_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
    
    try:
        # This should raise an error about missing API key in strict mode
        controller = ClaudeController(strict_mode=True)
        print("❌ Expected error for missing API key, but initialization succeeded")
    except ValueError as e:
        print(f"✓ Correctly caught missing API key error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Restore the original key if it existed
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key


async def test_claude_controller_validation():
    """Test input validation in Claude controller"""
    print("\nTesting input validation...")
    
    # Set a fake API key so we can test validation logic  
    original_key = os.environ.get("ANTHROPIC_API_KEY", "")
    os.environ["ANTHROPIC_API_KEY"] = "fake-key-for-validation-test"
    
    try:
        # Test empty message - create controller with fake key to bypass config check
        controller = ClaudeController(strict_mode=False) 
        
        request = aiapirequest(
            job_id="test-job-1",
            user_id="test-user-1",
            model="claude-3-sonnet-20240229",
            message=""
        )
        
        result = await controller.process_request(request)
        
        if not result.success and "Message cannot be empty" in result.error_message:
            print("✓ Correctly validated empty message")
        else:
            print(f"❌ Expected empty message validation to fail, got: {result}")
            
        # Test empty model
        request = aiapirequest(
            job_id="test-job-2", 
            user_id="test-user-2",
            model="",
            message="Test message"
        )
        
        result = await controller.process_request(request)
        
        if not result.success and "Model cannot be empty" in result.error_message:
            print("✓ Correctly validated empty model")
        else:
            print(f"❌ Expected empty model validation to fail, got: {result}")
            
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
    finally:
        # Restore the original key if it existed
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]


async def test_claude_controller_without_real_api():
    """Test Claude controller behavior with fake API key (expect auth error)"""
    print("\nTesting Claude controller with fake API key...")
    
    # Set a fake API key
    original_key = os.environ.get("ANTHROPIC_API_KEY", "")
    os.environ["ANTHROPIC_API_KEY"] = "fake-anthropic-key-for-testing"
    
    try:
        request = aiapirequest(
            job_id="test-job-3",
            user_id="test-user-3", 
            model="claude-3-sonnet-20240229",
            message="Hello, how are you?"
        )
        
        result = await process_claude_request(request)
        
        # We expect this to fail due to authentication error
        if not result.success and ("authentication" in result.error_message.lower() or "api" in result.error_message.lower()):
            print("✓ Correctly handled authentication error with fake API key")
        else:
            print(f"❌ Expected authentication error, got: {result}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        # Restore the original key if it existed
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]


async def run_tests():
    """Run all Claude controller tests"""
    print("Starting Claude Controller tests...\n")
    
    await test_claude_controller_without_api_key()
    await test_claude_controller_validation() 
    await test_claude_controller_without_real_api()
    
    print("\nClaude Controller tests completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())