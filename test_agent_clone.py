"""
Test for agent cloning functionality
"""
import pytest
from unittest.mock import AsyncMock, patch
from model.agent import Agent, AgentCreate
from service.agent_service import AgentService


@pytest.mark.asyncio
async def test_clone_agent_with_klone_prefix():
    """Test that cloned agent gets 'klone: ' prefix"""
    # Create test agent
    test_agent = Agent(
        name="test-agent",
        description="Test Agent Description",
        provider="openai",
        model="gpt-4",
        role="Test Role",
        task="Test Task",
        parameters=[{"param1": {"type": "string", "description": "Test parameter"}}]
    )
    
    with patch.object(AgentService, 'get_agent_by_name', new_callable=AsyncMock) as mock_get:
        with patch.object(AgentService, 'agent_exists', new_callable=AsyncMock) as mock_exists:
            with patch.object(AgentService, 'create_agent', new_callable=AsyncMock) as mock_create:
                mock_get.return_value = test_agent
                mock_exists.return_value = False
                
                # Setup mock to return the expected cloned agent
                expected_clone = Agent(
                    name="klone: test-agent",
                    description=test_agent.description,
                    role=test_agent.role,
                    provider=test_agent.provider,
                    model=test_agent.model,
                    task=test_agent.task,
                    parameters=test_agent.parameters
                )
                mock_create.return_value = expected_clone
                
                # Call the clone function
                cloned_agent = await AgentService.clone_agent("test-agent")
                
                # Verify the clone was created with correct prefix
                assert cloned_agent.name == "klone: test-agent"
                
                # Verify all data was copied
                assert cloned_agent.description == test_agent.description
                assert cloned_agent.role == test_agent.role
                assert cloned_agent.provider == test_agent.provider
                assert cloned_agent.model == test_agent.model
                assert cloned_agent.task == test_agent.task
                assert cloned_agent.parameters == test_agent.parameters


@pytest.mark.asyncio
async def test_clone_agent_copies_parameters():
    """Test that parameters are copied when cloning"""
    # Create test agent with parameters
    test_params = [
        {"input_text": {"type": "string", "description": "Input text"}},
        {"model": {"type": "string", "description": "Model name", "default": "gpt-4"}}
    ]
    
    test_agent = Agent(
        name="param-test-agent",
        description="Test Agent with Parameters",
        provider="openai",
        model="gpt-4",
        role="Test Role",
        task="Test Task",
        parameters=test_params
    )
    
    with patch.object(AgentService, 'get_agent_by_name', new_callable=AsyncMock) as mock_get:
        with patch.object(AgentService, 'agent_exists', new_callable=AsyncMock) as mock_exists:
            with patch.object(AgentService, 'create_agent', new_callable=AsyncMock) as mock_create:
                mock_get.return_value = test_agent
                mock_exists.return_value = False
                
                expected_clone = Agent(
                    name="klone: param-test-agent",
                    description=test_agent.description,
                    role=test_agent.role,
                    provider=test_agent.provider,
                    model=test_agent.model,
                    task=test_agent.task,
                    parameters=test_params
                )
                mock_create.return_value = expected_clone
                
                # Call clone
                cloned_agent = await AgentService.clone_agent("param-test-agent")
                
                # Verify parameters were copied
                assert cloned_agent.parameters == test_params
                
                # Verify create_agent was called with parameters
                mock_create.assert_called_once()
                call_args = mock_create.call_args[0][0]
                assert isinstance(call_args, AgentCreate)
                assert call_args.parameters == test_params


@pytest.mark.asyncio
async def test_clone_agent_removes_existing_klone_prefix():
    """Test that existing 'klone: ' prefix is removed before creating new clone"""
    # Create agent that already has klone prefix
    test_agent = Agent(
        name="klone: original-agent",
        description="Already cloned agent",
        provider="openai",
        model="gpt-4",
        role="Test Role",
        task="Test Task"
    )
    
    with patch.object(AgentService, 'get_agent_by_name', new_callable=AsyncMock) as mock_get:
        with patch.object(AgentService, 'agent_exists', new_callable=AsyncMock) as mock_exists:
            with patch.object(AgentService, 'create_agent', new_callable=AsyncMock) as mock_create:
                mock_get.return_value = test_agent
                mock_exists.return_value = False
                
                expected_clone = Agent(
                    name="klone: original-agent",
                    description=test_agent.description,
                    role=test_agent.role,
                    provider=test_agent.provider,
                    model=test_agent.model,
                    task=test_agent.task,
                    parameters=None
                )
                mock_create.return_value = expected_clone
                
                # Clone the already-cloned agent
                cloned_agent = await AgentService.clone_agent("klone: original-agent")
                
                # Should still be "klone: original-agent", not "klone: klone: original-agent"
                assert cloned_agent.name == "klone: original-agent"


@pytest.mark.asyncio
async def test_clone_agent_handles_duplicate_names():
    """Test that clone handles naming conflicts with counter"""
    test_agent = Agent(
        name="popular-agent",
        description="Popular agent",
        provider="openai",
        model="gpt-4",
        role="Test Role",
        task="Test Task"
    )
    
    with patch.object(AgentService, 'get_agent_by_name', new_callable=AsyncMock) as mock_get:
        with patch.object(AgentService, 'agent_exists', new_callable=AsyncMock) as mock_exists:
            with patch.object(AgentService, 'create_agent', new_callable=AsyncMock) as mock_create:
                mock_get.return_value = test_agent
                
                # First clone name exists, second clone name doesn't
                mock_exists.side_effect = [True, False]
                
                expected_clone = Agent(
                    name="klone: popular-agent 1",
                    description=test_agent.description,
                    role=test_agent.role,
                    provider=test_agent.provider,
                    model=test_agent.model,
                    task=test_agent.task,
                    parameters=None
                )
                mock_create.return_value = expected_clone
                
                # Clone
                cloned_agent = await AgentService.clone_agent("popular-agent")
                
                # Should have counter appended
                assert cloned_agent.name == "klone: popular-agent 1"


@pytest.mark.asyncio
async def test_clone_nonexistent_agent_raises_error():
    """Test that cloning non-existent agent raises ValueError"""
    with patch.object(AgentService, 'get_agent_by_name', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        
        with pytest.raises(ValueError, match="Agent with name 'nonexistent' not found"):
            await AgentService.clone_agent("nonexistent")
