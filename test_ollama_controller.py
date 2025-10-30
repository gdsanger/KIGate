"""
Tests for Ollama API Controller
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from controller.api_ollama import OllamaController, process_ollama_request


@pytest.mark.asyncio
async def test_ollama_controller_initialization():
    """Test that OllamaController initializes correctly"""
    controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
    assert controller.api_url == "http://localhost:11434"
    assert controller.client is not None


@pytest.mark.asyncio
async def test_ollama_controller_no_url_non_strict():
    """Test that OllamaController handles missing URL in non-strict mode"""
    controller = OllamaController(strict_mode=False, api_url=None)
    assert controller.api_url is None
    assert controller.client is None


@pytest.mark.asyncio
async def test_ollama_controller_no_url_strict():
    """Test that OllamaController raises error with missing URL in strict mode"""
    with pytest.raises(ValueError, match="Ollama API URL is required"):
        OllamaController(strict_mode=True, api_url=None)


@pytest.mark.asyncio
async def test_ollama_process_request_success():
    """Test successful request processing"""
    request = aiapirequest(
        job_id="test-job-1",
        user_id="test-user",
        model="llama3.2",
        message="Hello, Ollama!"
    )
    
    # Mock the Ollama client and response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Hello! How can I help you?"
    mock_response.message = mock_message
    
    mock_client.chat = AsyncMock(return_value=mock_response)
    
    controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
    controller.client = mock_client
    
    result = await controller.process_request(request)
    
    assert result.success is True
    assert result.content == "Hello! How can I help you?"
    assert result.job_id == "test-job-1"
    assert result.user_id == "test-user"
    assert result.error_message is None
    
    # Verify the client was called with correct parameters
    mock_client.chat.assert_called_once()
    call_args = mock_client.chat.call_args
    assert call_args.kwargs['model'] == "llama3.2"
    assert len(call_args.kwargs['messages']) == 1
    assert call_args.kwargs['messages'][0]['role'] == 'user'
    assert call_args.kwargs['messages'][0]['content'] == "Hello, Ollama!"


@pytest.mark.asyncio
async def test_ollama_process_request_no_client():
    """Test request processing when client is not initialized"""
    request = aiapirequest(
        job_id="test-job-2",
        user_id="test-user",
        model="llama3.2",
        message="Hello, Ollama!"
    )
    
    controller = OllamaController(strict_mode=False, api_url=None)
    
    result = await controller.process_request(request)
    
    assert result.success is False
    assert "Ollama API URL is not configured" in result.error_message
    assert result.content == ""


@pytest.mark.asyncio
async def test_ollama_process_request_with_prompt_and_role():
    """Test request processing with prompt and role fields"""
    request = aiapirequest(
        job_id="test-job-3",
        user_id="test-user",
        model="llama3.2",
        prompt="What is the capital of France?",
        role="user"
    )
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "The capital of France is Paris."
    mock_response.message = mock_message
    
    mock_client.chat = AsyncMock(return_value=mock_response)
    
    controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
    controller.client = mock_client
    
    result = await controller.process_request(request)
    
    assert result.success is True
    assert result.content == "The capital of France is Paris."


@pytest.mark.asyncio
async def test_ollama_process_request_empty_message():
    """Test request processing with empty message"""
    request = aiapirequest(
        job_id="test-job-4",
        user_id="test-user",
        model="llama3.2",
        message=""
    )
    
    controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
    controller.client = MagicMock()
    
    result = await controller.process_request(request)
    
    assert result.success is False
    # Empty string message is treated as no message provided
    assert "Either 'message' or 'prompt' field must be provided" in result.error_message


@pytest.mark.asyncio
async def test_ollama_process_request_api_error():
    """Test request processing when API returns error"""
    request = aiapirequest(
        job_id="test-job-5",
        user_id="test-user",
        model="llama3.2",
        message="Hello"
    )
    
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(side_effect=Exception("Connection error"))
    
    controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
    controller.client = mock_client
    
    result = await controller.process_request(request)
    
    assert result.success is False
    assert "Unexpected error" in result.error_message
    assert "Connection error" in result.error_message


@pytest.mark.asyncio
async def test_process_ollama_request_convenience_function():
    """Test the convenience function process_ollama_request"""
    request = aiapirequest(
        job_id="test-job-6",
        user_id="test-user",
        model="llama3.2",
        message="Test message"
    )
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Response from convenience function"
    mock_response.message = mock_message
    
    mock_client.chat = AsyncMock(return_value=mock_response)
    
    with patch('controller.api_ollama.OllamaController') as MockController:
        mock_controller_instance = MagicMock()
        mock_controller_instance.process_request = AsyncMock(return_value=aiapiresult(
            job_id="test-job-6",
            user_id="test-user",
            content="Response from convenience function",
            success=True
        ))
        MockController.return_value = mock_controller_instance
        
        result = await process_ollama_request(request, api_url="http://localhost:11434")
        
        assert result.success is True
        assert result.content == "Response from convenience function"
