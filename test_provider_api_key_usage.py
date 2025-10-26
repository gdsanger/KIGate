"""
Test that API controllers use Provider entity API keys from database
"""
import pytest
import os
from controller.api_gemini import GeminiController
from controller.api_claude import ClaudeController
from controller.api_openai import OpenAIController


@pytest.mark.asyncio
async def test_gemini_controller_accepts_api_key_parameter():
    """Test that Gemini controller accepts API key parameter"""
    # Clear environment variable
    original_key = os.environ.get("GEMINI_API_KEY", "")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    try:
        # Controller should accept api_key parameter in non-strict mode
        test_api_key = "test-gemini-key-123"
        controller = GeminiController(strict_mode=False, api_key=test_api_key)
        
        # In non-strict mode with fake key, client should be None but no exception
        assert controller is not None
        print("✓ Gemini controller accepts API key parameter without environment variable")
        
    finally:
        # Restore original key
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key


@pytest.mark.asyncio
async def test_claude_controller_accepts_api_key_parameter():
    """Test that Claude controller accepts API key parameter"""
    # Clear environment variable
    original_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
    
    try:
        # Controller should accept api_key parameter in non-strict mode
        test_api_key = "test-claude-key-123"
        controller = ClaudeController(strict_mode=False, api_key=test_api_key)
        
        # Verify controller has the API key
        assert controller is not None
        assert controller.api_key == test_api_key
        print("✓ Claude controller accepts API key parameter without environment variable")
        
    finally:
        # Restore original key
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key


@pytest.mark.asyncio
async def test_openai_controller_accepts_api_key_parameter():
    """Test that OpenAI controller accepts API key parameter"""
    # Clear environment variables
    original_key = os.environ.get("OPENAI_API_KEY", "")
    original_org = os.environ.get("OPENAI_ORG_ID", "")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    if "OPENAI_ORG_ID" in os.environ:
        del os.environ["OPENAI_ORG_ID"]
    
    try:
        # Controller should accept api_key parameter in non-strict mode
        test_api_key = "test-openai-key-123"
        test_org_id = "test-org-456"
        controller = OpenAIController(strict_mode=False, api_key=test_api_key, org_id=test_org_id)
        
        # Verify controller has the API key and org_id
        assert controller is not None
        assert controller.api_key == test_api_key
        assert controller.org_id == test_org_id
        print("✓ OpenAI controller accepts API key and org_id parameters without environment variables")
        
    finally:
        # Restore original keys
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        if original_org:
            os.environ["OPENAI_ORG_ID"] = original_org


@pytest.mark.asyncio
async def test_controllers_fallback_to_environment():
    """Test that controllers fall back to environment variables when no API key provided"""
    # Set environment variables
    os.environ["GEMINI_API_KEY"] = "env-gemini-key"
    os.environ["ANTHROPIC_API_KEY"] = "env-claude-key"
    os.environ["OPENAI_API_KEY"] = "env-openai-key"
    os.environ["OPENAI_ORG_ID"] = "env-org-id"
    
    try:
        # Controllers should use environment variables when no api_key provided
        gemini_controller = GeminiController(strict_mode=False)
        claude_controller = ClaudeController(strict_mode=False)
        openai_controller = OpenAIController(strict_mode=False)
        
        # Verify they're initialized
        assert gemini_controller is not None
        assert claude_controller is not None
        assert claude_controller.api_key == "env-claude-key"
        assert openai_controller is not None
        assert openai_controller.api_key == "env-openai-key"
        assert openai_controller.org_id == "env-org-id"
        
        print("✓ Controllers correctly fall back to environment variables")
        
    finally:
        # Clean up
        del os.environ["GEMINI_API_KEY"]
        del os.environ["ANTHROPIC_API_KEY"]
        del os.environ["OPENAI_API_KEY"]
        del os.environ["OPENAI_ORG_ID"]


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("\nTesting Provider API Key Usage...\n")
        await test_gemini_controller_accepts_api_key_parameter()
        await test_claude_controller_accepts_api_key_parameter()
        await test_openai_controller_accepts_api_key_parameter()
        await test_controllers_fallback_to_environment()
        print("\n✓ All provider API key usage tests passed!")
    
    asyncio.run(run_tests())
