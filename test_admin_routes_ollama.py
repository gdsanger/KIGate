"""
Test for admin routes Ollama integration with database provider configuration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from model.provider import Provider
from model.agent import Agent
from model.aiapiresult import aiapiresult
from model.aiapirequest import aiapirequest


@pytest.mark.asyncio
async def test_admin_test_agent_passes_db_to_send_ai_request():
    """Test that test_agent endpoint passes db parameter to send_ai_request"""
    from admin_routes import test_agent
    from fastapi import Request
    
    # Create test agent
    test_agent_obj = Agent(
        name="test-ollama-agent",
        description="Test Ollama Agent",
        provider="ollama",
        model="llama3.2",
        role="Test Role",
        task="Test Task"
    )
    
    # Mock successful AI result
    mock_ai_result = aiapiresult(
        job_id="test-job-id",
        user_id="test-user-id",
        content="Test response from Ollama",
        success=True
    )
    
    # Mock database session
    mock_db = MagicMock()
    
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.json = AsyncMock(return_value={"message": "Test message"})
    
    with patch('admin_routes.AgentService.get_agent_by_name', new_callable=AsyncMock) as mock_get_agent:
        with patch('admin_routes.send_ai_request', new_callable=AsyncMock) as mock_send_ai_request:
            mock_get_agent.return_value = test_agent_obj
            mock_send_ai_request.return_value = mock_ai_result
            
            # Call the function directly
            result = await test_agent(
                name="test-ollama-agent",
                request=mock_request,
                db=mock_db,
                admin_user="test-admin"
            )
            
            # Verify send_ai_request was called with db parameter
            mock_send_ai_request.assert_called_once()
            call_args = mock_send_ai_request.call_args
            
            # Check that three arguments were passed (request, provider, db)
            assert len(call_args.args) == 3 or (len(call_args.args) == 2 and 'db' in call_args.kwargs)
            
            # Verify the db parameter is not None
            if len(call_args.args) == 3:
                assert call_args.args[2] is mock_db, "db parameter should be the mock_db"
            else:
                assert call_args.kwargs.get('db') is mock_db, "db parameter should be the mock_db"


@pytest.mark.asyncio
async def test_admin_test_agent_ollama_uses_database_api_url():
    """Test that Ollama provider uses api_url from database"""
    from service.ai_service import send_ai_request
    
    # This is an integration-style test that verifies the full flow
    test_request = aiapirequest(
        job_id="test-job-id",
        user_id="test-user-id",
        model="llama3.2",
        message="Test message"
    )
    
    # Create test provider with Ollama configuration
    test_provider = Provider(
        id="test-provider-id",
        name="Test Ollama",
        provider_type="ollama",
        api_url="http://test-ollama:11434",
        is_active=True
    )
    
    # Mock database session
    mock_db = MagicMock()
    mock_execute = AsyncMock()
    mock_db.execute = mock_execute
    
    # Configure mock to return provider
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = test_provider
    mock_execute.return_value = mock_scalar
    
    # Mock the Ollama process_ollama_request to capture api_url
    captured_api_url = None
    
    async def mock_process_ollama_request(request, api_url=None):
        nonlocal captured_api_url
        captured_api_url = api_url
        return aiapiresult(
            job_id=request.job_id,
            user_id=request.user_id,
            content="Test response",
            success=True
        )
    
    with patch('controller.api_ollama.process_ollama_request', new=mock_process_ollama_request):
        # Call send_ai_request with db parameter
        result = await send_ai_request(test_request, "ollama", db=mock_db)
        
        # Verify the api_url was passed to the Ollama controller
        assert captured_api_url == "http://test-ollama:11434", f"Expected api_url from database, got {captured_api_url}"
        assert result.success is True

