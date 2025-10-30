"""
Integration tests for Redis Cache with Agent Execution endpoint
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio

from service.cache_service import CacheService
from model.agent_execution import AgentExecutionRequest, AgentExecutionResponse, CacheMetadata
from model.agent import Agent
import config


@pytest.fixture
def mock_redis():
    """Fixture for mocked Redis client"""
    with patch('service.cache_service.redis.Redis') as mock:
        redis_instance = MagicMock()
        redis_instance.ping.return_value = True
        redis_instance.get.return_value = None
        redis_instance.setex.return_value = True
        redis_instance.set.return_value = True
        redis_instance.delete.return_value = 1
        redis_instance.exists.return_value = False
        redis_instance.ttl.return_value = 3600
        redis_instance.scan_iter.return_value = iter([])
        mock.return_value = redis_instance
        yield redis_instance


@pytest.fixture
def reset_cache_service():
    """Reset CacheService singleton state between tests"""
    CacheService._redis_client = None
    CacheService._initialized = False
    yield
    CacheService._redis_client = None
    CacheService._initialized = False


class TestAgentExecutionCacheIntegration:
    """Integration tests for agent execution with Redis cache"""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation_with_parameters(self):
        """Test cache key generation includes parameters correctly"""
        key1 = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Translate this",
            parameters={"from": "en", "to": "de"}
        )
        
        key2 = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Translate this",
            parameters={"to": "de", "from": "en"}  # Same params, different order
        )
        
        assert key1 == key2, "Parameter order should not affect cache key"
    
    @pytest.mark.asyncio
    async def test_cache_workflow_complete(self, mock_redis, reset_cache_service):
        """Test complete cache workflow: miss -> store -> hit"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            # Step 1: Cache miss
            result = await CacheService.get_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello world"
            )
            assert result is None, "Should get cache miss on first access"
            
            # Step 2: Store result
            success = await CacheService.set_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello world",
                result="AI generated response",
                status="completed",
                job_id="job-123",
                ttl=3600
            )
            assert success is True, "Should successfully cache result"
            
            # Simulate cache hit by setting up mock return value
            cached_data = json.dumps({
                "result": "AI generated response",
                "status": "completed",
                "job_id": "job-123",
                "metadata": {
                    "cached_at": "2024-01-01T00:00:00",
                    "agent_name": "test-agent",
                    "provider": "openai",
                    "model": "gpt-4"
                }
            })
            mock_redis.get.return_value = cached_data
            mock_redis.ttl.return_value = 3600
            
            # Step 3: Cache hit
            result = await CacheService.get_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello world"
            )
            assert result is not None, "Should get cache hit on second access"
            response, metadata = result
            assert response == "AI generated response"
    
    @pytest.mark.asyncio
    async def test_different_users_get_separate_cache(self, mock_redis, reset_cache_service):
        """Test that different users have separate cache entries"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            key1 = CacheService._generate_cache_key(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user1",
                message="Hello"
            )
            
            key2 = CacheService._generate_cache_key(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user2",  # Different user
                message="Hello"
            )
            
            assert key1 != key2, "Different users should have different cache keys"
    
    @pytest.mark.asyncio
    async def test_different_agents_get_separate_cache(self, mock_redis, reset_cache_service):
        """Test that different agents have separate cache entries"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            key1 = CacheService._generate_cache_key(
                agent_name="agent-a",
                provider="openai",
                model="gpt-4",
                user_id="user1",
                message="Hello"
            )
            
            key2 = CacheService._generate_cache_key(
                agent_name="agent-b",  # Different agent
                provider="openai",
                model="gpt-4",
                user_id="user1",
                message="Hello"
            )
            
            assert key1 != key2, "Different agents should have different cache keys"
    
    @pytest.mark.asyncio
    async def test_different_providers_get_separate_cache(self, mock_redis, reset_cache_service):
        """Test that different providers have separate cache entries"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            key1 = CacheService._generate_cache_key(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user1",
                message="Hello"
            )
            
            key2 = CacheService._generate_cache_key(
                agent_name="test-agent",
                provider="anthropic",  # Different provider
                model="claude-3",
                user_id="user1",
                message="Hello"
            )
            
            assert key1 != key2, "Different providers should have different cache keys"
    
    @pytest.mark.asyncio
    async def test_error_status_uses_shorter_ttl(self, mock_redis, reset_cache_service):
        """Test that failed results use shorter TTL"""
        with patch.object(config, 'REDIS_ENABLED', True):
            with patch.object(config, 'CACHE_ERROR_TTL', 60):
                with patch.object(config, 'CACHE_DEFAULT_TTL', 3600):
                    CacheService.initialize()
                    
                    # Store failed result without explicit TTL
                    await CacheService.set_cached_result(
                        agent_name="test-agent",
                        provider="openai",
                        model="gpt-4",
                        user_id="user123",
                        message="Hello",
                        result="Error occurred",
                        status="failed",
                        job_id="job-error"
                    )
                    
                    # Check that error TTL was used
                    call_args = mock_redis.setex.call_args
                    assert call_args[0][1] == 60, "Failed status should use error TTL"
    
    @pytest.mark.asyncio
    async def test_success_status_uses_default_ttl(self, mock_redis, reset_cache_service):
        """Test that successful results use default TTL"""
        with patch.object(config, 'REDIS_ENABLED', True):
            with patch.object(config, 'CACHE_ERROR_TTL', 60):
                with patch.object(config, 'CACHE_DEFAULT_TTL', 3600):
                    CacheService.initialize()
                    
                    # Store successful result without explicit TTL
                    await CacheService.set_cached_result(
                        agent_name="test-agent",
                        provider="openai",
                        model="gpt-4",
                        user_id="user123",
                        message="Hello",
                        result="Success response",
                        status="completed",
                        job_id="job-success"
                    )
                    
                    # Check that default TTL was used
                    call_args = mock_redis.setex.call_args
                    assert call_args[0][1] == 3600, "Completed status should use default TTL"
    
    @pytest.mark.asyncio
    async def test_lock_prevents_concurrent_execution(self, mock_redis, reset_cache_service):
        """Test that lock mechanism prevents concurrent executions"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            cache_key = "test-cache-key"
            
            # First acquire should succeed
            acquired1 = await CacheService.acquire_lock(cache_key)
            assert acquired1 is True, "First lock acquisition should succeed"
            
            # Second acquire should fail (lock already held)
            mock_redis.set.return_value = None  # Simulate lock already exists
            acquired2 = await CacheService.acquire_lock(cache_key)
            assert acquired2 is False, "Second lock acquisition should fail"
            
            # Release lock
            released = await CacheService.release_lock(cache_key)
            assert released is True, "Lock release should succeed"
    
    @pytest.mark.asyncio
    async def test_cache_clear_with_pattern(self, mock_redis, reset_cache_service):
        """Test clearing cache with specific pattern"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            # Mock some keys matching pattern
            test_keys = [
                "kigate:v1:agent-exec:agent1:openai:gpt-4:u:user1:h:hash1",
                "kigate:v1:agent-exec:agent2:openai:gpt-4:u:user1:h:hash2"
            ]
            mock_redis.scan_iter.return_value = iter(test_keys)
            mock_redis.delete.return_value = len(test_keys)
            
            deleted = CacheService.clear_cache("kigate:v1:agent-exec:*")
            
            assert deleted == 2, "Should delete all matching keys"
            mock_redis.delete.assert_called_once_with(*test_keys)
    
    def test_agent_execution_request_validation(self):
        """Test that AgentExecutionRequest validates cache parameters"""
        # Valid request with all cache parameters
        request = AgentExecutionRequest(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            message="Hello",
            user_id="user123",
            use_cache=True,
            force_refresh=False,
            cache_ttl=7200
        )
        
        assert request.use_cache is True
        assert request.force_refresh is False
        assert request.cache_ttl == 7200
    
    def test_agent_execution_request_defaults(self):
        """Test default values for cache parameters"""
        request = AgentExecutionRequest(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            message="Hello",
            user_id="user123"
        )
        
        assert request.use_cache is True, "use_cache should default to True"
        assert request.force_refresh is False, "force_refresh should default to False"
        assert request.cache_ttl is None, "cache_ttl should default to None"
    
    def test_agent_execution_response_cache_metadata(self):
        """Test AgentExecutionResponse includes cache metadata"""
        cache_meta = CacheMetadata(
            status="hit",
            cached_at="2024-01-01T00:00:00",
            ttl=3600
        )
        
        response = AgentExecutionResponse(
            job_id="job-123",
            agent="test-agent",
            provider="openai",
            model="gpt-4",
            status="completed",
            result="Test response",
            cache=cache_meta
        )
        
        assert response.cache is not None
        assert response.cache.status == "hit"
        assert response.cache.ttl == 3600
