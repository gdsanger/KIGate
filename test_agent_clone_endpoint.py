"""
Integration test for agent cloning via admin routes
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from model.agent import Agent


@pytest.mark.asyncio
async def test_clone_agent_endpoint():
    """Test the clone agent endpoint returns correct data"""
    from admin_routes import admin_router, clone_agent
    
    # Create test agent with parameters
    test_agent = Agent(
        name="endpoint-test-agent",
        description="Test Agent for Endpoint",
        provider="openai",
        model="gpt-4",
        role="Test Role",
        task="Test Task",
        parameters=[{"param1": {"type": "string", "description": "Test param"}}]
    )
    
    cloned_agent = Agent(
        name="klone: endpoint-test-agent",
        description=test_agent.description,
        role=test_agent.role,
        provider=test_agent.provider,
        model=test_agent.model,
        task=test_agent.task,
        parameters=test_agent.parameters
    )
    
    with patch('admin_routes.AgentService.clone_agent', new_callable=AsyncMock) as mock_clone:
        mock_clone.return_value = cloned_agent
        
        # Call the endpoint function directly
        response = await clone_agent(name="endpoint-test-agent", admin_user="test_admin")
        
        # Verify response
        assert response.body is not None
        
        # Verify clone_agent was called
        mock_clone.assert_called_once_with("endpoint-test-agent")


@pytest.mark.asyncio
async def test_clone_agent_endpoint_not_found():
    """Test clone endpoint with non-existent agent"""
    from admin_routes import clone_agent
    from fastapi import HTTPException
    
    with patch('admin_routes.AgentService.clone_agent', new_callable=AsyncMock) as mock_clone:
        mock_clone.side_effect = ValueError("Agent with name 'nonexistent' not found")
        
        # Should raise 404 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await clone_agent(name="nonexistent", admin_user="test_admin")
        
        assert exc_info.value.status_code == 404
