"""
Tests for Redis Cache Service
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from service.cache_service import CacheService
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


class TestCacheService:
    """Test suite for CacheService"""
    
    def test_initialize_with_redis_enabled(self, mock_redis, reset_cache_service):
        """Test cache service initialization when Redis is enabled"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            assert CacheService._initialized is True
            assert CacheService.is_available() is True
            mock_redis.ping.assert_called_once()
    
    def test_initialize_with_redis_disabled(self, reset_cache_service):
        """Test cache service initialization when Redis is disabled"""
        with patch.object(config, 'REDIS_ENABLED', False):
            CacheService.initialize()
            assert CacheService._initialized is True
            assert CacheService.is_available() is False
    
    def test_initialize_with_connection_error(self, reset_cache_service):
        """Test cache service handles connection errors gracefully"""
        with patch('service.cache_service.redis.Redis') as mock:
            redis_instance = MagicMock()
            redis_instance.ping.side_effect = Exception("Connection failed")
            mock.return_value = redis_instance
            
            with patch.object(config, 'REDIS_ENABLED', True):
                CacheService.initialize()
                assert CacheService._initialized is True
                assert CacheService.is_available() is False
    
    def test_generate_cache_key(self):
        """Test cache key generation"""
        key = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Hello world",
            parameters={"param1": "value1"}
        )
        
        assert key.startswith("kigate:v1:agent-exec:")
        assert "test-agent" in key
        assert "openai" in key
        assert "gpt-4" in key
        assert "user123" in key
        assert ":h:" in key
    
    def test_generate_cache_key_consistency(self):
        """Test that same inputs generate same cache key"""
        key1 = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Hello",
            parameters={"a": "1", "b": "2"}
        )
        
        key2 = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Hello",
            parameters={"b": "2", "a": "1"}  # Different order
        )
        
        assert key1 == key2, "Keys should be identical regardless of parameter order"
    
    def test_generate_cache_key_different_inputs(self):
        """Test that different inputs generate different cache keys"""
        key1 = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Hello"
        )
        
        key2 = CacheService._generate_cache_key(
            agent_name="test-agent",
            provider="openai",
            model="gpt-4",
            user_id="user123",
            message="Goodbye"  # Different message
        )
        
        assert key1 != key2, "Different messages should generate different keys"
    
    @pytest.mark.asyncio
    async def test_get_cached_result_miss(self, mock_redis, reset_cache_service):
        """Test cache miss scenario"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            mock_redis.get.return_value = None
            
            result = await CacheService.get_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello"
            )
            
            assert result is None
            mock_redis.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cached_result_hit(self, mock_redis, reset_cache_service):
        """Test cache hit scenario"""
        import json
        
        cached_data = json.dumps({
            "result": "Cached response",
            "status": "completed",
            "job_id": "job123",
            "metadata": {
                "cached_at": "2024-01-01T00:00:00",
                "agent_name": "test-agent",
                "provider": "openai",
                "model": "gpt-4"
            }
        })
        
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            mock_redis.get.return_value = cached_data
            mock_redis.ttl.return_value = 3600
            
            result = await CacheService.get_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello"
            )
            
            assert result is not None
            response, metadata = result
            assert response == "Cached response"
            assert metadata["cached_at"] == "2024-01-01T00:00:00"
            assert metadata["ttl"] == 3600
    
    @pytest.mark.asyncio
    async def test_set_cached_result(self, mock_redis, reset_cache_service):
        """Test caching a result"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            success = await CacheService.set_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello",
                result="AI response",
                status="completed",
                job_id="job123",
                ttl=3600
            )
            
            assert success is True
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 3600  # TTL
    
    @pytest.mark.asyncio
    async def test_set_cached_result_with_error_status(self, mock_redis, reset_cache_service):
        """Test caching uses shorter TTL for error status"""
        with patch.object(config, 'REDIS_ENABLED', True):
            with patch.object(config, 'CACHE_ERROR_TTL', 60):
                CacheService.initialize()
                
                success = await CacheService.set_cached_result(
                    agent_name="test-agent",
                    provider="openai",
                    model="gpt-4",
                    user_id="user123",
                    message="Hello",
                    result="Error message",
                    status="failed",
                    job_id="job123"
                )
                
                assert success is True
                call_args = mock_redis.setex.call_args
                assert call_args[0][1] == 60  # Error TTL
    
    @pytest.mark.asyncio
    async def test_acquire_lock(self, mock_redis, reset_cache_service):
        """Test acquiring a lock"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            mock_redis.set.return_value = True
            
            acquired = await CacheService.acquire_lock("test-key")
            
            assert acquired is True
            mock_redis.set.assert_called_once()
            call_kwargs = mock_redis.set.call_args[1]
            assert call_kwargs['nx'] is True
    
    @pytest.mark.asyncio
    async def test_acquire_lock_already_held(self, mock_redis, reset_cache_service):
        """Test acquiring a lock that's already held"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            mock_redis.set.return_value = None  # Lock already exists
            
            acquired = await CacheService.acquire_lock("test-key")
            
            assert acquired is False
    
    @pytest.mark.asyncio
    async def test_release_lock(self, mock_redis, reset_cache_service):
        """Test releasing a lock"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            
            released = await CacheService.release_lock("test-key")
            
            assert released is True
            mock_redis.delete.assert_called_once()
    
    def test_clear_cache(self, mock_redis, reset_cache_service):
        """Test clearing cache entries"""
        with patch.object(config, 'REDIS_ENABLED', True):
            CacheService.initialize()
            mock_redis.scan_iter.return_value = iter(["key1", "key2", "key3"])
            mock_redis.delete.return_value = 3
            
            deleted = CacheService.clear_cache()
            
            assert deleted == 3
            mock_redis.scan_iter.assert_called_once()
            mock_redis.delete.assert_called_once()
    
    def test_get_lock_key(self):
        """Test lock key generation"""
        cache_key = "kigate:v1:agent-exec:test"
        lock_key = CacheService._get_lock_key(cache_key)
        
        assert lock_key == "lock:kigate:v1:agent-exec:test"
    
    @pytest.mark.asyncio
    async def test_cache_not_available_graceful_handling(self, reset_cache_service):
        """Test that cache operations handle unavailable Redis gracefully"""
        with patch.object(config, 'REDIS_ENABLED', False):
            CacheService.initialize()
            
            # Should return None without errors
            result = await CacheService.get_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello"
            )
            assert result is None
            
            # Should return False without errors
            success = await CacheService.set_cached_result(
                agent_name="test-agent",
                provider="openai",
                model="gpt-4",
                user_id="user123",
                message="Hello",
                result="response",
                status="completed",
                job_id="job123"
            )
            assert success is False
