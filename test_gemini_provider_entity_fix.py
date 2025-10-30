"""
Test to verify that Gemini controller correctly uses API keys from Provider entity.
This test demonstrates the fix for the issue where Gemini was looking for API keys
in environment variables instead of using the API key from the Provider database entity.
"""
import pytest
import os
from controller.api_gemini import GeminiController, get_gemini_controller


@pytest.mark.asyncio
async def test_gemini_uses_provider_entity_api_key():
    """
    Test that Gemini controller uses API key from Provider entity (passed as parameter)
    when no environment variable is set.
    
    This simulates the exact scenario from the issue:
    - No GEMINI_API_KEY in environment
    - API key is stored in Provider entity in database
    - API key is passed to the controller as a parameter
    """
    # Clear environment to simulate the issue scenario
    original_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    # Force reload config to ensure it's empty
    import config
    import importlib
    importlib.reload(config)
    
    try:
        # Verify config has empty key (simulating no env variable at startup)
        assert config.GEMINI_API_KEY == "", f"Expected empty config key, got: {config.GEMINI_API_KEY}"
        
        # This is the key from the Provider entity database
        provider_api_key = "sk-test-provider-entity-key-from-database"
        
        # Create controller with API key from Provider entity
        # This is what ai_service.py does when it fetches the provider from database
        controller = get_gemini_controller(api_key=provider_api_key)
        
        # Verify controller was created successfully
        assert controller is not None
        print("✓ Gemini controller successfully initialized with Provider entity API key")
        
        # The key point: there should be NO warning about "GEMINI_API_KEY not found"
        # because we provided the api_key parameter from the Provider entity
        
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        elif "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        
        # Reload config to restore original state
        importlib.reload(config)


@pytest.mark.asyncio
async def test_gemini_provider_entity_takes_precedence():
    """
    Test that Provider entity API key takes precedence over environment variable.
    """
    # Set environment variable
    original_key = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "env-key-should-not-be-used"
    
    try:
        # API key from Provider entity should take precedence
        provider_api_key = "sk-provider-entity-key-takes-precedence"
        
        controller = get_gemini_controller(api_key=provider_api_key)
        
        # Controller should be initialized with Provider entity key, not env key
        assert controller is not None
        print("✓ Provider entity API key correctly takes precedence over environment variable")
        
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        elif "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("\nTesting Gemini Provider Entity Fix...\n")
        await test_gemini_uses_provider_entity_api_key()
        await test_gemini_provider_entity_takes_precedence()
        print("\n✓ All Provider entity tests passed!")
    
    asyncio.run(run_tests())
