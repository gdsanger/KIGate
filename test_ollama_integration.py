"""
Tests for Ollama integration in AI service
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from service.ai_service import send_ai_request


@pytest.mark.asyncio
async def test_ollama_normalization():
    """Test that 'ollama' is normalized correctly"""
    request = aiapirequest(
        job_id="test-job-ollama-1",
        user_id="test-user",
        model="llama3.2",
        message="test message"
    )
    
    mock_result = aiapiresult(
        job_id="test-job-ollama-1",
        user_id="test-user",
        content="test response",
        success=True
    )
    
    with patch('controller.api_ollama.process_ollama_request', new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = mock_result
        
        # Test with "ollama"
        result = await send_ai_request(request, "ollama")
        
        # Verify ollama controller was called
        mock_ollama.assert_called_once()
        assert result.success is True
        assert result.content == "test response"


@pytest.mark.asyncio
async def test_ollama_variations():
    """Test that various ollama name variations are normalized correctly"""
    request = aiapirequest(
        job_id="test-job-ollama-2",
        user_id="test-user",
        model="llama3.2",
        message="test message"
    )
    
    mock_result = aiapiresult(
        job_id="test-job-ollama-2",
        user_id="test-user",
        content="test response",
        success=True
    )
    
    test_variations = [
        "ollama",
        "Ollama",
        "OLLAMA",
        "ollama (local)",
        "Ollama (local)",
        "Ollama (Local)",
        "OLLAMA (LOCAL)",
        " ollama ",
        "ollama (loakl)",  # Test typo handling
        "Ollama (loakl)",
    ]
    
    for provider_name in test_variations:
        with patch('controller.api_ollama.process_ollama_request', new_callable=AsyncMock) as mock_ollama:
            mock_ollama.return_value = mock_result
            
            result = await send_ai_request(request, provider_name)
            
            # Verify ollama controller was called for each variation
            mock_ollama.assert_called_once()
            assert result.success is True, f"Failed for provider: {provider_name}"


@pytest.mark.asyncio
async def test_ollama_with_database_config():
    """Test that ollama uses api_url from database provider configuration"""
    from model.provider import Provider
    from unittest.mock import ANY
    
    request = aiapirequest(
        job_id="test-job-ollama-3",
        user_id="test-user",
        model="llama3.2",
        message="test message"
    )
    
    mock_result = aiapiresult(
        job_id="test-job-ollama-3",
        user_id="test-user",
        content="test response from ollama",
        success=True
    )
    
    # Create a mock database session
    mock_db = MagicMock()
    mock_execute = AsyncMock()
    mock_db.execute = mock_execute
    
    # Create a mock provider entity
    mock_provider = Provider(
        id="test-provider-id",
        name="Test Ollama",
        provider_type="ollama",
        api_url="http://localhost:11434",
        is_active=True
    )
    
    # Configure the mock to return the provider
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = mock_provider
    mock_execute.return_value = mock_scalar
    
    with patch('controller.api_ollama.process_ollama_request', new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = mock_result
        
        result = await send_ai_request(request, "ollama", db=mock_db)
        
        # Verify ollama controller was called with the api_url from database
        mock_ollama.assert_called_once_with(request, api_url="http://localhost:11434")
        assert result.success is True
        assert result.content == "test response from ollama"
