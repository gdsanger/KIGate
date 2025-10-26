"""
Integration test to verify that Gemini API key from database works correctly
This simulates the exact scenario described in the issue where:
1. The API key is stored in the Provider entity in the database
2. The API key is NOT in environment variables
3. The ai_service fetches the provider from DB and passes the key to the controller
"""
import pytest
import os
import importlib
from unittest.mock import AsyncMock, MagicMock, patch
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from service.ai_service import send_ai_request
from model.provider import Provider


def reload_config():
    """Helper function to reload config module to pick up environment changes"""
    import config
    importlib.reload(config)


@pytest.mark.asyncio
async def test_gemini_with_database_api_key_no_env():
    """Test that Gemini works with API key from database when env var is not set"""
    
    # Clear environment variable to simulate the issue scenario
    original_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    # Reload config to ensure it picks up the cleared environment
    reload_config()
    
    try:
        # Verify environment variable is not set
        import config
        assert os.environ.get("GEMINI_API_KEY", "") == ""
        assert config.GEMINI_API_KEY == ""
        
        # Create a mock database session
        mock_db = AsyncMock()
        
        # Create a mock provider with API key (simulating database storage)
        mock_provider = Provider(
            id="test-provider-id",
            name="Google Gemini",
            provider_type="gemini",
            api_key="test-database-api-key-12345",  # This is the key from the database
            is_active=True
        )
        
        # Mock the database query to return our provider
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_provider
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Create a request
        request = aiapirequest(
            job_id="test-job-123",
            user_id="admin-test-admin",
            model="gemini-pro",
            message="Test message"
        )
        
        # Mock the Gemini API call since we don't have a real API key
        with patch('google.generativeai.configure') as mock_configure, \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            
            # Mock the model instance
            mock_model_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test response from Gemini"
            mock_response.usage_metadata = MagicMock()
            mock_response.usage_metadata.total_token_count = 100
            mock_model_instance.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model_instance
            
            # Call send_ai_request with the database session
            result = await send_ai_request(request, "Google Gemini", db=mock_db)
            
            # Verify that genai.configure was called with the database API key
            mock_configure.assert_called()
            call_args = mock_configure.call_args
            assert call_args is not None
            # The api_key should be from the database
            assert call_args[1]['api_key'] == "test-database-api-key-12345"
            
            # Verify the result is successful
            assert result.success == True
            assert result.content == "Test response from Gemini"
            assert result.job_id == request.job_id
            assert result.user_id == request.user_id
            
            print("✓ Gemini successfully used API key from database without environment variable")
        
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        
        # Reload config to restore original state
        reload_config()


@pytest.mark.asyncio
async def test_gemini_error_message_when_no_api_key_anywhere():
    """Test that appropriate error is shown when no API key is available"""
    
    # Clear environment variable
    original_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    
    # Reload config
    reload_config()
    
    try:
        # Create a mock database session that returns no provider
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No provider found
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Create a request
        request = aiapirequest(
            job_id="test-job-456",
            user_id="test-user",
            model="gemini-pro",
            message="Test message"
        )
        
        # Call send_ai_request - should fail gracefully
        result = await send_ai_request(request, "gemini", db=mock_db)
        
        # Verify the result shows configuration error
        assert result.success == False
        assert "not configured" in result.error_message.lower()
        assert result.job_id == request.job_id
        
        print("✓ Appropriate error message shown when no API key is available")
        
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        
        reload_config()


@pytest.mark.asyncio
async def test_provider_precedence_order():
    """Test that API key sources are checked in correct order: parameter > environment > config"""
    
    # Set environment variable
    original_key = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "env-var-key"
    
    # Reload config to pick up env var
    reload_config()
    
    try:
        # Create request
        request = aiapirequest(
            job_id="test-job-789",
            user_id="test-user",
            model="gemini-pro",
            message="Test message"
        )
        
        # Create mock DB with provider that has different API key
        mock_db = AsyncMock()
        mock_provider = Provider(
            id="test-id",
            name="Gemini",
            provider_type="gemini",
            api_key="database-key",  # This should take precedence
            is_active=True
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_provider
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock the Gemini API
        with patch('google.generativeai.configure') as mock_configure, \
             patch('google.generativeai.GenerativeModel'):
            
            # Call send_ai_request
            result = await send_ai_request(request, "gemini", db=mock_db)
            
            # Verify the database key was used (not the env var)
            mock_configure.assert_called()
            call_args = mock_configure.call_args
            assert call_args[1]['api_key'] == "database-key"
            
            print("✓ API key precedence order is correct: database > environment > config")
        
    finally:
        # Restore original environment
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        elif "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        
        reload_config()


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("\nTesting Gemini Database API Key Integration...\n")
        await test_gemini_with_database_api_key_no_env()
        await test_gemini_error_message_when_no_api_key_anywhere()
        await test_provider_precedence_order()
        print("\n✓ All integration tests passed!")
    
    asyncio.run(run_tests())
