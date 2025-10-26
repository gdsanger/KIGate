"""
Tests for AI service provider name normalization
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from service.ai_service import send_ai_request


@pytest.mark.asyncio
async def test_google_gemini_normalization():
    """Test that 'Google Gemini' is normalized to 'gemini'"""
    request = aiapirequest(
        job_id="test-job-1",
        user_id="test-user",
        model="gemini-pro",
        message="test message"
    )
    
    # Mock the gemini controller
    mock_result = aiapiresult(
        job_id="test-job-1",
        user_id="test-user",
        content="test response",
        success=True
    )
    
    with patch('controller.api_gemini.process_gemini_request', new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_result
        
        # Test with "Google Gemini" (with capital letters and space)
        result = await send_ai_request(request, "Google Gemini")
        
        # Verify gemini controller was called
        mock_gemini.assert_called_once_with(request)
        assert result.success is True
        assert result.content == "test response"


@pytest.mark.asyncio
async def test_gemini_variations():
    """Test that various gemini name variations are normalized correctly"""
    request = aiapirequest(
        job_id="test-job-2",
        user_id="test-user",
        model="gemini-pro",
        message="test message"
    )
    
    mock_result = aiapiresult(
        job_id="test-job-2",
        user_id="test-user",
        content="test response",
        success=True
    )
    
    test_variations = [
        "gemini",
        "Gemini",
        "GEMINI",
        "google gemini",
        "Google Gemini",
        "GOOGLE GEMINI",
        " Google Gemini ",  # with spaces
    ]
    
    for provider_name in test_variations:
        with patch('controller.api_gemini.process_gemini_request', new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = mock_result
            
            result = await send_ai_request(request, provider_name)
            
            # Verify gemini controller was called for each variation
            mock_gemini.assert_called_once_with(request)
            assert result.success is True, f"Failed for provider: {provider_name}"


@pytest.mark.asyncio
async def test_openai_normalization():
    """Test that 'OpenAI' variations are normalized correctly"""
    request = aiapirequest(
        job_id="test-job-3",
        user_id="test-user",
        model="gpt-4",
        message="test message"
    )
    
    mock_result = aiapiresult(
        job_id="test-job-3",
        user_id="test-user",
        content="test response",
        success=True
    )
    
    test_variations = ["openai", "OpenAI", "OPENAI", " openai "]
    
    for provider_name in test_variations:
        with patch('controller.api_openai.process_openai_request', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = mock_result
            
            result = await send_ai_request(request, provider_name)
            
            mock_openai.assert_called_once_with(request)
            assert result.success is True, f"Failed for provider: {provider_name}"


@pytest.mark.asyncio
async def test_claude_normalization():
    """Test that 'Claude' and 'Anthropic Claude' variations are normalized correctly"""
    request = aiapirequest(
        job_id="test-job-4",
        user_id="test-user",
        model="claude-3-opus",
        message="test message"
    )
    
    mock_result = aiapiresult(
        job_id="test-job-4",
        user_id="test-user",
        content="test response",
        success=True
    )
    
    test_variations = [
        "claude",
        "Claude",
        "CLAUDE",
        "anthropic claude",
        "Anthropic Claude",
        "ANTHROPIC CLAUDE",
    ]
    
    for provider_name in test_variations:
        with patch('controller.api_claude.process_claude_request', new_callable=AsyncMock) as mock_claude:
            mock_claude.return_value = mock_result
            
            result = await send_ai_request(request, provider_name)
            
            mock_claude.assert_called_once_with(request)
            assert result.success is True, f"Failed for provider: {provider_name}"


@pytest.mark.asyncio
async def test_unsupported_provider():
    """Test that unsupported provider returns error with proper message"""
    request = aiapirequest(
        job_id="test-job-5",
        user_id="test-user",
        model="some-model",
        message="test message"
    )
    
    result = await send_ai_request(request, "unsupported-provider")
    
    assert result.success is False
    assert "Unsupported AI provider" in result.error_message
    assert "unsupported-provider" in result.error_message


@pytest.mark.asyncio
async def test_import_error_handling():
    """Test that import errors are handled properly"""
    request = aiapirequest(
        job_id="test-job-6",
        user_id="test-user",
        model="gpt-4",
        message="test message"
    )
    
    with patch('controller.api_openai.process_openai_request', side_effect=ImportError("Module not found")):
        result = await send_ai_request(request, "openai")
        
        assert result.success is False
        assert "controller not available" in result.error_message


@pytest.mark.asyncio
async def test_general_exception_handling():
    """Test that general exceptions are handled properly"""
    request = aiapirequest(
        job_id="test-job-7",
        user_id="test-user",
        model="gpt-4",
        message="test message"
    )
    
    with patch('controller.api_openai.process_openai_request', new_callable=AsyncMock) as mock_openai:
        mock_openai.side_effect = Exception("Unexpected error")
        
        result = await send_ai_request(request, "openai")
        
        assert result.success is False
        assert "Error processing request" in result.error_message
